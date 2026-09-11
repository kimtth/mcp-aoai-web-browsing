"""Fail explicitly rather than silently executing SDK 1.x as a v2 demonstration."""

from importlib.metadata import PackageNotFoundError, version


def require_sdk_v2() -> None:
    try:
        installed = version("mcp")
    except PackageNotFoundError:
        installed = "not installed"
    if installed != "2.2.0":
        raise SystemExit(
            f"This sample requires mcp==2.2.0; found {installed}. "
            "Install this folder's isolated environment through the approved package proxy. "
            "If that release is unavailable, run python -m unittest tests.test_auth for the SDK-independent "
            "fixture checks. Those checks are NOT SDK v2 integration verification."
        )