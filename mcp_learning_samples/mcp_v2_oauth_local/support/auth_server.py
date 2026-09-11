"""Loopback-only, auto-approving OAuth fixture. NEVER deploy as an identity service."""

import argparse
import json
import re
import secrets
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit

from support.auth_rules import ISSUER, REDIRECT, RESOURCE, SCOPE, challenge


class Authority:
    def __init__(self, issuer: str = ISSUER, scenario: str = "valid") -> None:
        self.issuer = issuer
        self.scenario = scenario
        self.clients: dict[str, dict[str, Any]] = {}
        self.codes: dict[str, dict[str, Any]] = {}
        self.tokens: dict[str, dict[str, Any]] = {}
        self.token_requests = 0

    def metadata(self) -> dict[str, Any]:
        return {
            "issuer": self.issuer,
            "authorization_endpoint": self.issuer + "/authorize",
            "token_endpoint": self.issuer + "/token",
            "registration_endpoint": self.issuer + "/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "token_endpoint_auth_methods_supported": ["none"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": [SCOPE],
            "authorization_response_iss_parameter_supported": True,
            "client_id_metadata_document_supported": False,
        }

    def register(self, data: dict[str, Any]) -> dict[str, Any]:
        if (data.get("application_type") != "native"
                or data.get("redirect_uris") != [REDIRECT]
                or data.get("token_endpoint_auth_method") != "none"
                or data.get("grant_types") != ["authorization_code"]
                or data.get("response_types") != ["code"]):
            raise ValueError("invalid_client_metadata")
        client_id = secrets.token_urlsafe(24)
        record = {**data, "client_id": client_id}
        self.clients[client_id] = record
        return record

    def authorize(self, data: dict[str, str]) -> str:
        if data.get("client_id") not in self.clients:
            raise ValueError("invalid_client")
        if (data.get("redirect_uri") != REDIRECT
                or data.get("response_type") != "code"
                or data.get("resource") != RESOURCE
                or data.get("scope") != SCOPE
                or data.get("code_challenge_method") != "S256"
                or not re.fullmatch(r"[A-Za-z0-9_-]{43}", data.get("code_challenge", ""))
                or not data.get("state")):
            raise ValueError("invalid_request")
        code = secrets.token_urlsafe(32)
        self.codes[code] = {**data, "expires_at": time.time() + 60}
        response = {"code": code, "state": data["state"]}
        if self.scenario != "missing-issuer":
            response["iss"] = self.issuer if self.scenario == "valid" else self.issuer + "/wrong"
        return REDIRECT + "?" + urlencode(response)

    def exchange(self, data: dict[str, str]) -> dict[str, Any]:
        self.token_requests += 1
        # Consume even a failed exchange: a code cannot be probed/reused indefinitely.
        grant = self.codes.pop(data.get("code", ""), None)
        verifier = data.get("code_verifier", "")
        if (grant is None or grant["expires_at"] <= time.time()
                or data.get("grant_type") != "authorization_code"
                or not re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", verifier)
                or data.get("client_id") != grant["client_id"]
                or data.get("redirect_uri") != grant["redirect_uri"]
                or data.get("resource") != grant["resource"]
                or not secrets.compare_digest(challenge(verifier), grant["code_challenge"])):
            raise ValueError("invalid_grant")
        token = secrets.token_urlsafe(32)
        self.tokens[token] = {
            "client_id": grant["client_id"], "scope": grant["scope"],
            "aud": grant["resource"], "iss": self.issuer,
            "exp": int(time.time()) + 300,
        }
        return {"access_token": token, "token_type": "Bearer", "expires_in": 300, "scope": SCOPE}

    def introspect(self, token: str) -> dict[str, Any]:
        record = self.tokens.get(token)
        if record is None or record["exp"] <= time.time():
            return {"active": False}
        return {"active": True, **record}


def make_server(port: int = 8020, scenario: str = "valid") -> HTTPServer:
    authority = Authority(scenario=scenario)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass  # Never log URLs with authorization codes, form bodies, or tokens.

        def respond(self, status: int, data: dict[str, Any], **headers: str) -> None:
            body = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self) -> bool:
            return (self.headers.get("Host") == urlsplit(authority.issuer).netloc
                    and self.headers.get("Origin") is None)

        def do_GET(self) -> None:
            if not self.valid_host():
                self.respond(403, {"error": "forbidden"})
                return
            parsed = urlsplit(self.path)
            try:
                if parsed.path == "/.well-known/oauth-authorization-server":
                    self.respond(200, authority.metadata())
                elif parsed.path == "/authorize":
                    values = parse_qs(parsed.query, keep_blank_values=True)
                    if any(len(value) != 1 for value in values.values()):
                        raise ValueError("invalid_request")
                    location = authority.authorize({k: v[0] for k, v in values.items()})
                    self.respond(302, {}, Location=location)
                elif parsed.path == "/stats":
                    self.respond(200, {"token_requests": authority.token_requests})
                else:
                    self.respond(404, {"error": "not_found"})
            except ValueError as error:
                self.respond(400, {"error": str(error)})

        def do_POST(self) -> None:
            if not self.valid_host():
                self.respond(403, {"error": "forbidden"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    raise ValueError("invalid_request")
                body = self.rfile.read(length).decode("utf-8")
                if self.path == "/register":
                    data = json.loads(body)
                    if not isinstance(data, dict):
                        raise ValueError("invalid_client_metadata")
                    self.respond(201, authority.register(data))
                    return
                values = parse_qs(body, keep_blank_values=True)
                if any(len(value) != 1 for value in values.values()):
                    raise ValueError("invalid_request")
                data = {k: v[0] for k, v in values.items()}
                if self.path == "/token":
                    self.respond(200, authority.exchange(data))
                elif self.path == "/introspect":
                    # Intentionally unauthenticated LOCAL fixture, not a production endpoint.
                    self.respond(200, authority.introspect(data.get("token", "")))
                else:
                    self.respond(404, {"error": "not_found"})
            except ValueError:
                self.respond(400, {"error": "invalid_request_or_grant"})

    server = HTTPServer(("127.0.0.1", port), Handler)
    authority.issuer = f"http://127.0.0.1:{server.server_port}"
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=["valid", "wrong-issuer", "missing-issuer"], default="valid")
    args = parser.parse_args()
    with make_server(scenario=args.scenario) as server:
        print(f"LOCAL AUTO-APPROVING FIXTURE {ISSUER}; scenario={args.scenario}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass