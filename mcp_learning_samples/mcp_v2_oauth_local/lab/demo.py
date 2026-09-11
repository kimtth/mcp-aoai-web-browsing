"""Runnable OAuth fixture lab WITHOUT MCP SDK. This does not test an MCP server."""

from support.auth_rules import RESOURCE

from lab.lab_support import exercise, fixture, request

if __name__ == "__main__":
    print("SDK-INDEPENDENT OAUTH FIXTURE LAB (not MCP v2 integration)")
    for scenario in ["valid", "wrong-issuer", "missing-issuer"]:
        with fixture(scenario) as issuer:
            try:
                token = exercise(issuer)
            except ValueError as error:
                if scenario == "valid":
                    raise
                print(f"{scenario}: REJECTED - {error}")
            else:
                if scenario != "valid":
                    raise AssertionError("An invalid issuer was accepted")
                status, _, record = request(issuer + "/introspect",
                                            {"token": token["access_token"]}, form=True)
                assert status == 200 and record["active"] and record["aud"] == RESOURCE
                print("valid: token issued and resource binding confirmed (token redacted)")
            _, _, stats = request(issuer + "/stats")
            assert stats["token_requests"] == (1 if scenario == "valid" else 0)
            print("  token endpoint requests:", stats["token_requests"])