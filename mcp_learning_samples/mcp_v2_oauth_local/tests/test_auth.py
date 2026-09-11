"""Standard-library tests of the fixture/policy, NOT tests of OAuthClientProvider."""

import time
import unittest
from urllib.parse import urlencode

from lab.lab_support import exercise, fixture, request
from support.auth_rules import (
    ISSUER,
    REDIRECT,
    RESOURCE,
    SCOPE,
    callback_values,
    challenge,
    new_pkce,
    validate_callback,
)
from support.auth_server import Authority


class CallbackTests(unittest.TestCase):
    def test_issuer_matrix(self):
        for advertised, issuer, accepted in [
            (True, ISSUER, True), (True, None, False),
            (False, ISSUER, True), (False, None, True),
            (True, ISSUER + "/", False), (False, ISSUER + "/", False),
            (True, "HTTP://127.0.0.1:8020", False), (False, "", False),
        ]:
            with self.subTest(advertised=advertised, issuer=issuer):
                values = {"code": "example-code", "state": "expected"}
                if issuer is not None:
                    values["iss"] = issuer
                if accepted:
                    validate_callback(values, "expected", ISSUER, advertised)
                else:
                    with self.assertRaises(ValueError):
                        validate_callback(values, "expected", ISSUER, advertised)

    def test_state_and_error_responses(self):
        with self.assertRaisesRegex(ValueError, "state mismatch"):
            validate_callback({"iss": ISSUER, "state": "wrong", "code": "x"}, "expected", ISSUER, True)
        with self.assertRaisesRegex(ValueError, "issuer mismatch"):
            validate_callback({"iss": "wrong", "error": "untrusted-error"}, "expected", ISSUER, True)

    def test_decode_once_and_reject_duplicates(self):
        values = callback_values(REDIRECT + "?" + urlencode({"iss": ISSUER + "/%2f"}))
        self.assertEqual(values["iss"], ISSUER + "/%2f")
        with self.assertRaises(ValueError):
            callback_values(REDIRECT + "?iss=one&iss=two")
        with self.assertRaises(ValueError):
            callback_values("http://localhost:8022/callback?code=x")

    def test_pkce_known_vector(self):
        self.assertEqual(challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"),
                         "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")


class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.authority = Authority()
        self.registration = {
            "application_type": "native", "redirect_uris": [REDIRECT],
            "token_endpoint_auth_method": "none", "grant_types": ["authorization_code"],
            "response_types": ["code"],
        }
        self.client = self.authority.register(self.registration)["client_id"]

    def grant(self):
        verifier, digest = new_pkce()
        location = self.authority.authorize({
            "client_id": self.client, "redirect_uri": REDIRECT, "resource": RESOURCE,
            "scope": SCOPE, "response_type": "code", "state": "fixture-state",
            "code_challenge_method": "S256", "code_challenge": digest,
        })
        return {"grant_type": "authorization_code", "code": callback_values(location)["code"],
                "client_id": self.client, "redirect_uri": REDIRECT,
                "resource": RESOURCE, "code_verifier": verifier}

    def test_native_registration_required(self):
        for value in [None, "web"]:
            with self.assertRaises(ValueError):
                self.authority.register({**self.registration, "application_type": value})

    def test_resource_pkce_client_redirect_and_grant_binding(self):
        for key, value in [("resource", RESOURCE + "/other"), ("code_verifier", "x" * 64),
                           ("client_id", "other"), ("redirect_uri", REDIRECT + "/other"),
                           ("grant_type", "client_credentials")]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.authority.exchange({**self.grant(), key: value})

    def test_code_expiry_and_replay(self):
        data = self.grant()
        self.authority.codes[data["code"]]["expires_at"] = time.time() - 1
        with self.assertRaises(ValueError):
            self.authority.exchange(data)
        data = self.grant()
        self.authority.exchange(data)
        with self.assertRaises(ValueError):
            self.authority.exchange(data)

    def test_token_expiry_and_unknown_token(self):
        token = self.authority.exchange(self.grant())["access_token"]
        self.assertEqual(self.authority.introspect(token)["aud"], RESOURCE)
        self.authority.tokens[token]["exp"] = int(time.time()) - 1
        self.assertFalse(self.authority.introspect(token)["active"])
        self.assertFalse(self.authority.introspect("unknown")["active"])


class LocalHTTPTests(unittest.TestCase):
    def test_success_over_real_http(self):
        with fixture() as issuer:
            token = exercise(issuer)
            status, _, result = request(issuer + "/introspect", {"token": token["access_token"]}, form=True)
            self.assertEqual(status, 200)
            self.assertTrue(result["active"])
            self.assertEqual(result["iss"], issuer)
            self.assertEqual(result["aud"], RESOURCE)

    def test_bad_issuer_never_reaches_token_endpoint(self):
        for scenario in ["wrong-issuer", "missing-issuer"]:
            with self.subTest(scenario=scenario), fixture(scenario) as issuer:
                with self.assertRaises(ValueError):
                    exercise(issuer)
                _, _, stats = request(issuer + "/stats")
                self.assertEqual(stats["token_requests"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)