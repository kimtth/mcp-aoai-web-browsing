"""Optional stdlib lab infrastructure; no MCP SDK or MCP protocol implementation."""

import json
import secrets
from contextlib import contextmanager
from threading import Thread
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from support.auth_rules import (
    REDIRECT,
    RESOURCE,
    SCOPE,
    callback_values,
    new_pkce,
    validate_callback,
)
from support.auth_server import make_server


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url: str, data: dict | None = None, *, form: bool = False):
    """Fixture HTTP only; redirects are captured, not followed to another origin."""
    content = None if data is None else (
        urlencode(data).encode() if form else json.dumps(data).encode()
    )
    kind = "application/x-www-form-urlencoded" if form else "application/json"
    req = Request(url, data=content, headers={"Content-Type": kind})
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        response = opener.open(req, timeout=5)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.headers, json.load(response)


@contextmanager
def fixture(scenario: str = "valid"):
    """Use an OS-assigned loopback port; no external network or fixed-port conflict."""
    with make_server(port=0, scenario=scenario) as server:
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            worker.join(timeout=5)


def exercise(issuer: str) -> dict:
    status, _, metadata = request(issuer + "/.well-known/oauth-authorization-server")
    if status != 200 or metadata.get("issuer") != issuer:
        raise ValueError("Metadata issuer mismatch")
    # This demo's expected issuer is pinned to the locally started fixture.
    for key, path in [("authorization_endpoint", "/authorize"),
                      ("token_endpoint", "/token"), ("registration_endpoint", "/register")]:
        if metadata.get(key) != issuer + path:
            raise ValueError("Unexpected fixture endpoint")
    registration = {
        "redirect_uris": [REDIRECT], "application_type": "native",
        "token_endpoint_auth_method": "none", "grant_types": ["authorization_code"],
        "response_types": ["code"], "scope": SCOPE,
    }
    status, _, client = request(metadata["registration_endpoint"], registration)
    if status != 201:
        raise ValueError("Registration rejected")
    verifier, code_challenge = new_pkce()
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": client["client_id"], "redirect_uri": REDIRECT,
        "response_type": "code", "state": state, "scope": SCOPE, "resource": RESOURCE,
        "code_challenge": code_challenge, "code_challenge_method": "S256",
    }
    status, headers, _ = request(metadata["authorization_endpoint"] + "?" + urlencode(params))
    if status != 302:
        raise ValueError("Authorization rejected")
    values = callback_values(headers["Location"])
    validate_callback(values, state, metadata["issuer"],
                      metadata.get("authorization_response_iss_parameter_supported") is True)
    status, _, token = request(metadata["token_endpoint"], {
        "grant_type": "authorization_code", "code": values["code"],
        "client_id": client["client_id"], "redirect_uri": REDIRECT,
        "code_verifier": verifier, "resource": RESOURCE,
    }, form=True)
    if status != 200:
        raise ValueError("Token exchange rejected")
    return token