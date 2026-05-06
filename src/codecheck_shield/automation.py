from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from codecheck_shield.desktop import DesktopSettings, WindowsDesktopAutomation, load_desktop_calibration
from codecheck_shield.errors import AutomationFailure


@dataclass(slots=True)
class BrowserSettings:
    browser_channel: str
    user_data_dir: Path | None
    profile_directory: str | None
    headless: bool
    slow_mo_ms: int
    screenshot_dir: Path


@dataclass(slots=True)
class CdpSettings:
    cdp_url: str
    screenshot_dir: Path


@dataclass(slots=True)
class RequestSettings:
    cookie: str
    agency_id: str
    cftk: str
    operator: str
    platform: str
    screenshot_dir: Path
    request_delay_seconds: float = 0.0


class _CodeCheckFlow:
    _settings: Any

    def _run_issue_flow(self, page: Any, url: str, reason: str) -> None:
        page.goto(url, wait_until="domcontentloaded")
        page.get_by_role("button", name="修改问题状态").click()
        self._click_visible_text(page, "忽略问题")
        dialog = page.locator("[role='dialog']").last
        dialog.wait_for(state="visible")
        self._fill_comment(dialog, reason)
        dialog.get_by_role("button", name="确定").click()
        page.get_by_text("修改问题状态").wait_for(state="visible")

    def _automation_failure(self, status: str, message: str, page: Any | None) -> AutomationFailure:
        screenshot_path = ""
        if page is not None:
            self._settings.screenshot_dir.mkdir(parents=True, exist_ok=True)
            screenshot_file = self._settings.screenshot_dir / "last_failure.png"
            page.screenshot(path=str(screenshot_file), full_page=True)
            screenshot_path = str(screenshot_file)
        return AutomationFailure(status, message, screenshot_path)

    def _click_visible_text(self, page, text: str) -> None:
        candidates = [
            page.get_by_role("menuitem", name=text),
            page.get_by_role("option", name=text),
            page.get_by_text(text, exact=True),
        ]
        for locator in candidates:
            if locator.count():
                locator.first.click()
                return
        raise AutomationFailure("failed_select_ignore", f"Could not find clickable text: {text}")

    def _fill_comment(self, dialog, reason: str) -> None:
        candidates = [
            dialog.locator("textarea"),
            dialog.get_by_label("评论"),
            dialog.get_by_label("备注"),
            dialog.get_by_label("处理意见"),
            dialog.get_by_placeholder("评论"),
            dialog.get_by_placeholder("备注"),
        ]
        for locator in candidates:
            if locator.count():
                locator.first.fill(reason)
                return
        textboxes = dialog.get_by_role("textbox")
        if textboxes.count():
            textboxes.last.fill(reason)
            return
        raise AutomationFailure("failed_fill_comment", "Could not find comment input in dialog")


class PlaywrightAutomation(_CodeCheckFlow):
    def __init__(self, settings: BrowserSettings) -> None:
        self._settings = settings
        self._playwright_manager: Any | None = None
        self._playwright: Any | None = None
        self._context: Any | None = None

    def shield_issue(self, url: str, reason: str) -> None:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Playwright is not installed. Run `pip install -e .[automation]` and `playwright install chromium`."
            ) from exc

        try:
            if self._context is None:
                self._playwright_manager = sync_playwright()
                self._playwright = self._playwright_manager.start()
                browser_type = self._playwright.chromium
                launch_args = []
                if self._settings.profile_directory:
                    launch_args.append(f"--profile-directory={self._settings.profile_directory}")
                self._context = browser_type.launch_persistent_context(
                    user_data_dir=str(self._settings.user_data_dir),
                    channel=self._settings.browser_channel,
                    headless=self._settings.headless,
                    slow_mo=self._settings.slow_mo_ms,
                    args=launch_args,
                )
            page = self._context.new_page()
            try:
                self._run_issue_flow(page, url, reason)
            finally:
                page.close()
        except PlaywrightTimeoutError as exc:
            raise self._automation_failure("failed_timeout", str(exc), locals().get("page")) from exc
        except AutomationFailure:
            raise
        except Exception as exc:
            raise self._automation_failure("failed_automation", str(exc), locals().get("page")) from exc

    def close(self) -> None:
        if self._context is not None:
            self._context.close()
            self._context = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
        if self._playwright_manager is not None:
            self._playwright_manager = None

 
class CdpAttachAutomation(_CodeCheckFlow):
    def __init__(self, settings: CdpSettings) -> None:
        self._settings = settings
        self._playwright_manager: Any | None = None
        self._playwright: Any | None = None
        self._browser: Any | None = None

    def shield_issue(self, url: str, reason: str) -> None:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Playwright is not installed. Run `pip install -e .[automation]` and `playwright install chromium`."
            ) from exc

        try:
            if self._browser is None:
                self._playwright_manager = sync_playwright()
                self._playwright = self._playwright_manager.start()
                self._browser = self._playwright.chromium.connect_over_cdp(self._settings.cdp_url)
            if not self._browser.contexts:
                raise AutomationFailure(
                    "failed_connect_cdp",
                    "Connected to Chrome, but no browser context was available. Open at least one tab in the target Chrome window.",
                )
            context = self._browser.contexts[0]
            page = context.new_page()
            try:
                self._run_issue_flow(page, url, reason)
            finally:
                page.close()
        except PlaywrightTimeoutError as exc:
            raise self._automation_failure("failed_timeout", str(exc), locals().get("page")) from exc
        except AutomationFailure:
            raise
        except Exception as exc:
            raise self._automation_failure("failed_connect_cdp", str(exc), locals().get("page")) from exc

    def close(self) -> None:
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
        if self._browser is not None:
            self._browser = None
        if self._playwright_manager is not None:
            self._playwright_manager = None


class RequestsAutomation:
    def __init__(
        self,
        settings: RequestSettings,
        sender: Any | None = None,
        time_ms: Any | None = None,
        sleeper: Any | None = None,
    ) -> None:
        self._settings = settings
        self._sender = sender or urllib_request.urlopen
        self._time_ms = time_ms or (lambda: int(__import__("time").time() * 1000))
        self._sleep = sleeper or time.sleep

    @property
    def request_delay_seconds(self) -> float:
        return self._settings.request_delay_seconds

    def shield_issue(self, url: str, reason: str) -> None:
        defect = _parse_defect_url(url)
        endpoint = f"{defect['origin']}/codechecknew/report/v1/defect/issue-status?_={self._time_ms()}"
        payload = {
            "taskId": defect["task_id"],
            "status": 5,
            "comment": reason,
            "mergeKey": defect["merge_key"],
            "espaceUrl": defect["canonical_task_url"],
            "platform": self._settings.platform,
            "operator": self._settings.operator,
        }
        request = urllib_request.Request(
            endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._request_headers(defect, referer=defect["canonical_defect_url"], include_content_type=True),
            method="POST",
        )
        try:
            response = self._sender(request)
            self._ensure_http_success(response)
            body = self._read_response_body(response)
            self._handle_post_response_body(body, defect, reason)
            self._verify_issue_update(defect, reason)
        except AutomationFailure:
            raise
        except urllib_error.HTTPError as exc:
            raise AutomationFailure("failed_request", f"HTTP {exc.code}: {exc.reason}") from exc
        except Exception as exc:
            raise AutomationFailure("failed_request", str(exc)) from exc

    def close(self) -> None:
        return None

    def _request_headers(
        self,
        defect: dict[str, str],
        *,
        referer: str,
        include_content_type: bool,
    ) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Cookie": self._settings.cookie,
            "AgencyId": self._settings.agency_id,
            "cftk": self._settings.cftk,
            "Origin": defect["origin"],
            "Referer": referer,
            "X-Requested-With": "XMLHttpRequest",
            "X-Referer": "CodeCheckWeb",
            "X-Language": "zh-cn",
            "language": "zh-cn",
            "projectname": defect["region"],
        }
        if include_content_type:
            headers["Content-Type"] = "application/json; charset=UTF-8"
        return headers

    def _ensure_http_success(self, response: Any) -> None:
        status = getattr(response, "status", 200)
        if status >= 400:
            raise AutomationFailure("failed_request", f"HTTP {status}")

    def _read_response_body(self, response: Any) -> bytes:
        if hasattr(response, "read"):
            return response.read()
        return b""

    def _handle_post_response_body(self, body: bytes | str, defect: dict[str, str], reason: str) -> None:
        if not body:
            return
        payload = self._parse_json_body(body)
        if payload is None:
            return
        status = str(payload.get("status", "")).strip().lower()
        result = str(payload.get("result", "")).strip()
        if status == "success" or result == "修改成功":
            return
        if any(key in payload for key in ("status", "result", "message", "errorMsg", "errorMessage")):
            verification_payload = self._fetch_verification_payload(defect)
            classified = self._classify_request_failure(payload, verification_payload, reason)
            if classified is not None:
                raise classified
            raise AutomationFailure("failed_request", f"CodeCheck API rejected the request: {self._summarize_payload(payload)}")

    def _verify_issue_update(self, defect: dict[str, str], reason: str) -> None:
        payload = self._fetch_verification_payload(defect)
        if self._payload_contains_reason(payload, reason):
            return
        raise AutomationFailure(
            "failed_request",
            "CodeCheck API did not confirm the updated reason in follow-up verification",
        )

    def _fetch_verification_payload(self, defect: dict[str, str]) -> dict[str, Any]:
        endpoint = (
            f"{defect['origin']}/codechecknew/report/v1/defect"
            f"?defect_index={urllib_parse.quote(defect['defect_index'])}"
            f"&task_id={urllib_parse.quote(defect['task_id'])}"
            f"&merge_key={urllib_parse.quote(defect['merge_key'])}"
            f"&_={self._time_ms()}"
        )
        request = urllib_request.Request(
            endpoint,
            headers=self._request_headers(defect, referer=defect["canonical_defect_url"], include_content_type=False),
            method="GET",
        )
        response = self._sender(request)
        self._ensure_http_success(response)
        body = self._read_response_body(response)
        if not body:
            raise AutomationFailure("failed_request", "Verification request returned an empty response body")
        payload = self._parse_json_body(body)
        if payload is None:
            raise AutomationFailure("failed_request", f"Verification returned invalid JSON: {self._body_text(body)[:200]}")
        return payload

    def _classify_request_failure(
        self,
        post_payload: dict[str, Any],
        verification_payload: dict[str, Any],
        reason: str,
    ) -> AutomationFailure | None:
        if self._looks_unreachable_page(post_payload) or self._looks_unreachable_page(verification_payload):
            return AutomationFailure(
                "unreachable_page",
                f"CodeCheck could not find or access the defect page (not found): {self._best_failure_message(verification_payload, post_payload)}",
            )
        defect_status = self._extract_defect_status(verification_payload)
        if defect_status == "5":
            return AutomationFailure(
                "already_shielded",
                f"CodeCheck reports the issue is already shielded: {self._best_failure_message(post_payload, verification_payload)}",
            )
        if self._payload_contains_reason(verification_payload, reason):
            return AutomationFailure(
                "already_shielded",
                f"CodeCheck reports the issue is already shielded: {self._best_failure_message(post_payload, verification_payload)}",
            )
        return None

    def _parse_json_body(self, body: bytes | str) -> dict[str, Any] | None:
        text = self._body_text(body)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            return payload
        return None

    def _body_text(self, body: bytes | str) -> str:
        return body.decode("utf-8", errors="replace") if isinstance(body, bytes) else str(body)

    def _summarize_payload(self, payload: dict[str, Any]) -> str:
        nested_error = payload.get("error")
        nested_error_message = ""
        nested_error_reason = ""
        nested_error_code = ""
        if isinstance(nested_error, dict):
            nested_error_message = str(nested_error.get("message", "")).strip()
            nested_error_reason = str(nested_error.get("reason", "")).strip()
            nested_error_code = str(nested_error.get("code", "") or nested_error.get("error_code", "")).strip()
        message_parts = [
            str(payload.get("message", "")).strip(),
            str(payload.get("result", "")).strip(),
            str(payload.get("errorMsg", "")).strip(),
            str(payload.get("errorMessage", "")).strip(),
            nested_error_message,
            nested_error_reason,
            nested_error_code,
            str(payload.get("status", "")).strip(),
        ]
        message = " | ".join(part for part in message_parts if part)
        return message or json.dumps(payload, ensure_ascii=False)[:200]

    def _best_failure_message(self, *payloads: dict[str, Any]) -> str:
        for payload in payloads:
            message = self._summarize_payload(payload)
            if message:
                return message
        return "Unknown CodeCheck error"

    def _extract_defect_status(self, payload: dict[str, Any]) -> str:
        result = payload.get("result")
        if isinstance(result, dict):
            return str(result.get("defectStatus", "")).strip()
        return ""

    def _looks_unreachable_page(self, payload: dict[str, Any]) -> bool:
        status = str(payload.get("status", "")).strip().lower()
        top_level_error = str(payload.get("error", "")).strip().lower()
        top_level_message = str(payload.get("message", "")).strip().lower()
        nested_error = payload.get("error")
        nested_message = ""
        nested_reason = ""
        if isinstance(nested_error, dict):
            nested_message = str(nested_error.get("message", "")).strip().lower()
            nested_reason = str(nested_error.get("reason", "")).strip().lower()
        explicit_signals = (
            "不能在数据库中找到",
            "please ensure the last check contains this defect",
        )
        return (
            any(signal in nested_reason for signal in explicit_signals)
            or any(signal in nested_message for signal in explicit_signals)
            or (status == "404" and top_level_error == "not found")
            or (top_level_error == "not found" and bool(payload.get("path")))
            or (top_level_message == "not found" and bool(payload.get("path")))
        )

    def _payload_contains_reason(self, payload: Any, reason: str) -> bool:
        if isinstance(payload, dict):
            for value in payload.values():
                if self._payload_contains_reason(value, reason):
                    return True
            return False
        if isinstance(payload, list):
            return any(self._payload_contains_reason(item, reason) for item in payload)
        if isinstance(payload, str):
            return reason in payload
        return False


def build_automation(args) -> PlaywrightAutomation | CdpAttachAutomation | RequestsAutomation:
    if args.browser_mode == "requests":
        return RequestsAutomation(
            RequestSettings(
                cookie=_resolve_request_cookie(args.request_cookie, args.request_cookie_file),
                agency_id=args.agency_id,
                cftk=args.cftk,
                operator=args.request_operator,
                platform=args.request_platform,
                screenshot_dir=Path(os.path.expandvars(args.screenshot_dir)).expanduser(),
                request_delay_seconds=float(args.action_delay_seconds),
            )
        )

    if args.browser_mode == "windows-desktop":
        return WindowsDesktopAutomation(
            DesktopSettings(
                calibration=load_desktop_calibration(args.desktop_calibration_file),
                screenshot_dir=Path(os.path.expandvars(args.screenshot_dir)).expanduser(),
                page_load_seconds=args.page_load_seconds,
                action_delay_seconds=args.action_delay_seconds,
            )
        )

    if args.browser_mode == "attach-cdp":
        return CdpAttachAutomation(
            CdpSettings(
                cdp_url=args.cdp_url,
                screenshot_dir=Path(os.path.expandvars(args.screenshot_dir)).expanduser(),
            )
        )

    settings = BrowserSettings(
        browser_channel=args.browser_channel,
        user_data_dir=Path(os.path.expandvars(args.user_data_dir)).expanduser() if args.user_data_dir else None,
        profile_directory=args.profile_directory,
        headless=args.headless,
        slow_mo_ms=args.slow_mo_ms,
        screenshot_dir=Path(os.path.expandvars(args.screenshot_dir)).expanduser(),
    )
    return PlaywrightAutomation(settings)


def _resolve_request_cookie(cookie: str | None, cookie_file: str | None) -> str:
    if cookie:
        return cookie.strip()
    if cookie_file:
        return Path(os.path.expandvars(cookie_file)).expanduser().read_text(encoding="utf-8").strip()
    raise RuntimeError("Requests mode requires --request-cookie or --request-cookie-file.")


def _parse_defect_url(url: str) -> dict[str, str]:
    parsed = urllib_parse.urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    query = urllib_parse.parse_qs(parsed.query)
    try:
        project_index = parts.index("project")
        task_index = parts.index("task")
        defect_index = parts.index("defect")
    except ValueError as exc:
        raise RuntimeError(f"Unsupported defect detail URL: {url}") from exc
    project_id = parts[project_index + 1]
    task_segments = parts[task_index + 1:defect_index]
    if not task_segments:
        raise RuntimeError(f"Unsupported defect detail URL: {url}")
    if len(task_segments) == 1:
        task_path_prefix = ""
        task_id = task_segments[0]
    else:
        task_path_prefix = "/".join(task_segments[:-1])
        task_id = task_segments[-1]
    merge_key = parts[defect_index + 1]
    host_parts = parsed.netloc.split(".")
    region = host_parts[1] if len(host_parts) > 1 else "cn-north-4"
    defect_index_value = query.get("defectIndex", ["1"])[0]
    origin = f"{parsed.scheme}://{parsed.netloc}"
    canonical_defect_url = (
        f"{origin}/codechecknew/project/{project_id}/codecheck/task/{task_id}/defect/{merge_key}"
        f"?defectIndex={urllib_parse.quote(defect_index_value)}"
    )
    canonical_task_url = (
        f"{origin}/codechecknew/project/{project_id}/codecheck/task/{task_id}"
        "/defects?delayStatus=undefined&approver=undefined"
    )
    return {
        "origin": origin,
        "project_id": project_id,
        "task_id": task_id,
        "merge_key": merge_key,
        "defect_index": defect_index_value,
        "region": region,
        "task_path_prefix": task_path_prefix,
        "canonical_defect_url": canonical_defect_url,
        "canonical_task_url": canonical_task_url,
    }
