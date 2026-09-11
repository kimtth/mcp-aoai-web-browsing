"""Opt-in live GUI test: real Azure calls, MCP tools, Chromium and native capture.

Requires a configured Azure CLI login and Pillow on the capture process's path.
This is not included in offline unittest discovery. It makes billable API calls.
"""

import argparse
import asyncio
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from tkinter import END, Tk
from urllib.parse import parse_qs, urlencode, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

QUERY = "site:learn.microsoft.com/en-us/ Model Context Protocol"
SEARCH_URL = "https://www.google.com/search?" + urlencode(
    {"q": QUERY, "hl": "en", "lr": "lang_en"}
)
RESULT_SELECTOR = "#search a:has(h3)"
PROMPTS = (
    (f"Open this exact English Google search URL with playwright_navigate: {SEARCH_URL} . "
    "Do not change the query, add quotes, or navigate to another URL. Use playwright_evaluate "
    "to read the first two organic search results (#search a containing h3). Reply in English with each exact h3 title and "
    "displayed source name (not the tracking link). Keep it concise; "
    "use actual browser results, not prior knowledge."),
    ("Without navigating again, use playwright_evaluate to read the current search "
    "box query and first organic result title. Reply in English with those two values only."),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Native GUI capture currently requires Windows.")

    from loguru import logger
    from PIL import ImageGrab

    logger.remove()
    logger.add(sys.stderr, level="INFO", diagnose=False)
    # Capture fresh credentials into this process only; never log or save them.
    token = subprocess.check_output(
        ["az.cmd", "account", "get-access-token", "--resource",
         "https://cognitiveservices.azure.com/", "--query", "accessToken", "-o", "tsv"],
        text=True,
    ).strip()
    os.environ.update({
        "AZURE_OPEN_AI_ENDPOINT": args.endpoint,
        "AZURE_OPEN_AI_DEPLOYMENT_MODEL": args.deployment,
        "AZURE_OPENAI_AD_TOKEN": token,
        "AZURE_OPEN_AI_API_KEY": "",
        "OPENAI_TOKEN_LIMIT_PARAMETER": "max_completion_tokens",
        "OPENAI_TEMPERATURE": "",
    })

    from chatgui import ClientBridgeGUI

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    staging = tempfile.TemporaryDirectory(prefix="mcp-gui-e2e-")
    stage_dir = Path(staging.name)
    root = Tk()
    root.geometry("900x660+40+40")
    app = ClientBridgeGUI(root)
    pool = ThreadPoolExecutor(max_workers=1)
    started = time.monotonic()
    turn = 0
    sent = False
    verification = None
    capture = None
    failure = []
    report = None
    finished = False

    async def verify_browser():
        page = app.server.browser_manager.page
        assert page is not None, "No browser page was created by the MCP tool."
        title = await page.title()
        location = urlparse(page.url)
        assert location.hostname == "www.google.com", page.url
        assert location.path == "/search", page.url
        assert parse_qs(location.query).get("q") == [QUERY], page.url
        query = await page.locator('[name="q"]').first.input_value()
        assert query == QUERY, query
        language = await page.locator("html").get_attribute("lang")
        assert language and language.lower().startswith("en"), f"Expected English page: {language}"
        results = await page.locator(RESULT_SELECTOR).evaluate_all(
            "nodes => nodes.slice(0, 2).map(a => ({title: a.querySelector('h3').innerText.trim(), href: a.href, source: a.innerText}))"
        )
        assert len(results) == 2, "Two organic results not available; search may be blocked."
        for result in results:
            assert result["title"] and urlparse(result["href"]).scheme in {"http", "https"}
            assert "Microsoft Learn" in result["source"] and "learn.microsoft.com" in result["source"], result
            assert all(ord(char) < 128 for char in result["title"] if char.isalpha()), result
        messages = app.bridge.llm_client.messages
        calls = [call for message in messages for call in (message.get("tool_calls") or [])]
        names = [call.function.name for call in calls]
        assert names.count("playwright_navigate") == 1, names
        assert names.count("playwright_evaluate") >= 2, names
        tool_results = [message for message in messages if message["role"] == "tool"]
        assert len(tool_results) == len(calls), "Missing tool responses."
        assert {message["tool_call_id"] for message in tool_results} == {call.id for call in calls}
        for message in tool_results:
            assert not message["content"].startswith("Error"), message["content"]
        observed_results = []
        for message in tool_results:
            content = message["content"]
            if content.startswith("Execution result:\n"):
                payload = content.removeprefix("Execution result:\n").split("\n\nConsole output:")[0]
                content = json.dumps(json.loads(payload), ensure_ascii=False)
            observed_results.append(content)
        observed_results = "\n".join(observed_results)
        replies = [message["content"] for message in messages
                   if message["role"] == "assistant" and not message.get("tool_calls")]
        assert len(replies) == 2, replies
        for result in results:
            assert result["title"] in replies[0], "GUI answer does not match the real result title."
            assert "Microsoft Learn" in replies[0], "GUI answer does not match the displayed source."
            assert result["title"] in observed_results and "Microsoft Learn" in observed_results
        assert QUERY in replies[1] and results[0]["title"] in replies[1], replies[1]
        # Capture the very same page opened through MCP, not a new test browser.
        await page.set_viewport_size({"width": 1280, "height": 900})
        await page.screenshot(path=str(stage_dir / "original-browser.png"))
        return {
            "status": "passed",
            "observed_at": datetime.now(UTC).isoformat(),
            "deployment": args.deployment,
            "endpoint": args.endpoint,
            "interaction": "Tk input insertion and real Send button invocation",
            "mocks": False,
            "turns": 2,
            "page": {"url": page.url, "title": title, "language": language, "query": query, "results": results},
            "tool_calls": [{"id": call.id, "name": call.function.name,
                            "arguments": json.loads(call.function.arguments)} for call in calls],
            "tool_results": tool_results,
            "replies": replies,
        }

    def capture_window(hwnd):
        # PrintWindow captures this HWND even if another app covers its desktop area.
        image = ImageGrab.grab(window=hwnd)
        assert image.width >= 700 and image.height >= 400, image.size
        assert any(low != high for low, high in image.convert("RGB").getextrema()), "Blank capture."
        image.save(stage_dir / "original-gui.png")

    async def cleanup():
        await app.server.browser_manager.close()
        if hasattr(app, "bridge"):
            await app.bridge.mcp_client_session.disconnect()
            app.bridge.llm_client.client.close()
        app.server.llm_client.client.close()

    def finish(error=None):
        nonlocal finished
        if finished:
            return
        finished = True
        if error:
            failure.append(error)
        future = asyncio.run_coroutine_threadsafe(cleanup(), app.loop)

        def close_when_ready():
            if future.done():
                try:
                    future.result()
                except Exception as exc:
                    logger.exception("E2E cleanup failed")
                    failure.append(f"Cleanup failed: {exc}")
                app.close()
            else:
                root.after(100, close_when_ready)

        root.after(0, close_when_ready)

    def tick():
        nonlocal turn, sent, verification, capture, report
        try:
            assert time.monotonic() - started < 180, "GUI E2E timed out."
            if not hasattr(app, "bridge"):
                root.after(100, tick)
                return
            if turn < len(PROMPTS):
                if not sent:
                    # Real SDK, but bound test duration and disable transport retries.
                    app.bridge.llm_client.client = app.bridge.llm_client.client.with_options(
                        timeout=45, max_retries=0,
                    )
                    app.user_input.insert("1.0", PROMPTS[turn])
                    app.send_button.invoke()
                    assert not app.user_input.get("1.0", END).strip(), "Send did not clear input."
                    sent = True
                transcript = app.text_area.get("1.0", END)
                assert "Error:" not in transcript and "Error processing message:" not in transcript, transcript
                if transcript.count("Response:") == turn + 1:
                    turn += 1
                    sent = False
            elif verification is None:
                verification = asyncio.run_coroutine_threadsafe(verify_browser(), app.loop)
            elif verification.done() and capture is None:
                report = verification.result()
                transcript = app.text_area.get("1.0", END).strip()
                assert all(reply in transcript for reply in report["replies"])
                app.text_area.yview_moveto(0)
                root.update_idletasks()
                assert app.text_area.yview()[1] == 1.0, "Transcript clipped; enlarge GUI before capture."
                user32 = ctypes.windll.user32
                user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
                user32.GetAncestor.restype = ctypes.c_void_p
                hwnd = user32.GetAncestor(root.winfo_id(), 2)
                assert hwnd, "Native GUI window handle unavailable."
                report["transcript"] = transcript
                capture = pool.submit(capture_window, hwnd)
            elif capture is not None and capture.done():
                capture.result()
                report["screenshots"] = {}
                for name in ("original-gui.png", "original-browser.png"):
                    data = (stage_dir / name).read_bytes()
                    report["screenshots"][name] = {"sha256": hashlib.sha256(data).hexdigest()}
                    (output / name).write_bytes(data)
                (output / "original-e2e.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
                print("E2E PASSED: 2 real GUI turns; Azure -> MCP -> Chromium -> GUI.", flush=True)
                print(f"CAPTURE_DIR: {output}", flush=True)
                finish()
                return
            root.after(100, tick)
        except Exception as exc:
            logger.exception("E2E verification failed")
            finish(str(exc))

    root.protocol("WM_DELETE_WINDOW", lambda: finish("Test window closed before completion."))
    root.after(100, tick)
    root.mainloop()
    pool.shutdown(wait=True)
    staging.cleanup()
    if failure:
        raise RuntimeError("; ".join(failure))


if __name__ == "__main__":
    main()