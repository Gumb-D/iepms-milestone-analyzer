import datetime
import json
import os
from typing import Callable, Dict, Optional

try:
    import requests
except ImportError:
    requests = None

try:
    from .runtime_state import PollWindow, emit_run_state
except ImportError:  # Direct script execution
    from runtime_state import PollWindow, emit_run_state


RECORD_URL = "https://iepms.zte.com.cn/zte-crm-iepms-basebff/zte-crm-iepms-schedule/record"
EXPORT_URL = "https://iepms.zte.com.cn/zte-crm-iepms-basebff/zte-crm-iepms-schedule/schedule/export"
DOWNLOAD_URL = "https://iepms.zte.com.cn/zte-crm-iepms-basebff/zte-crm-iepms-schedule/record/download"


def _legacy_components():
    try:
        from .IEPMS_Milestone_Analyzer import PROJECT_CONFIGS, run_auth_server
    except ImportError:
        from IEPMS_Milestone_Analyzer import PROJECT_CONFIGS, run_auth_server
    return PROJECT_CONFIGS, run_auth_server


def _load_auth(auth_path: str) -> dict:
    with open(auth_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_cookies(cookie_string: str) -> dict:
    cookies = {}
    for item in cookie_string.split(";"):
        if "=" not in item:
            continue
        key, value = item.strip().split("=", 1)
        cookies[key] = value
    return cookies


def _auth_value(auth: dict, cookies: dict) -> str:
    value = auth.get("x_auth_value", "")
    if not value or "YOUR_AUTH_VALUE" in value:
        return cookies.get("ZTEDPGSSOCookie", cookies.get("UCSSSOToken", ""))
    return value


def _test_headers(auth: dict, cookies: dict) -> dict:
    return {
        "Accept": "application/json",
        "X-Auth-Value": _auth_value(auth, cookies),
        "X-Emp-No": auth.get("x_emp_no", "10265696"),
        "X-Lang-Id": "en_US",
        "X-Org-Id": "1",
        "X-Tenant-Id": "10001",
        "Internal": "1",
    }


def _base_headers(auth: dict, cookies: dict) -> dict:
    return {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6,ms;q=0.5",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Internal": "1",
        "Referer": "https://iepms.zte.com.cn/zte-crm-iepms-scheduleui/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "X-Auth-Value": _auth_value(auth, cookies),
        "X-Emp-No": auth.get("x_emp_no", "10265696"),
        "X-Lang-Id": "en_US",
        "X-Org-Id": "1",
        "X-Origin-ServiceName": "zte-crm-iepms-schedule",
        "X-Target-ServiceName": "zte-crm-iepms-schedule",
        "X-Tenant-Id": "10001",
    }


def _sync_auth(script_dir: str, auth_server: Callable[[str], None]) -> None:
    emit_run_state("WAITING_FOR_AUTH", action="click_sync_auth_bookmarklet")
    auth_server(script_dir)
    emit_run_state("AUTHENTICATED")


def _ensure_auth(
    script_dir: str,
    *,
    requests_module,
    auth_server: Callable[[str], None],
) -> dict:
    auth_path = os.path.join(script_dir, "api_auth.json")
    if not os.path.exists(auth_path):
        _sync_auth(script_dir, auth_server)

    auth = _load_auth(auth_path)
    cookies = _parse_cookies(auth.get("cookie", ""))
    params = {
        "operationType": "EXPORT",
        "pageNo": "1",
        "pageSize": "1",
        "bizType": "SCHEDULE",
    }

    try:
        response = requests_module.get(
            RECORD_URL,
            headers=_test_headers(auth, cookies),
            cookies=cookies,
            params=params,
            timeout=10,
        )
        unauthorized = response.status_code != 200
        if response.status_code == 200:
            code = response.json().get("code", {}).get("code", "")
            unauthorized = code != "0000"
        if unauthorized:
            print("Authentication token is expired or unauthorized.")
            _sync_auth(script_dir, auth_server)
            auth = _load_auth(auth_path)
    except Exception as exc:
        print(f"Connectivity test failed: {exc}. Starting authentication sync.")
        _sync_auth(script_dir, auth_server)
        auth = _load_auth(auth_path)

    return auth


def _submit_exports(auth: dict, project_configs: dict, requests_module) -> Dict[str, dict]:
    cookies = _parse_cookies(auth.get("cookie", ""))
    base_headers = _base_headers(auth, cookies)
    pending_files: Dict[str, dict] = {}

    emit_run_state("SUBMITTING_EXPORTS")
    print("\n========================================================")
    print("STEP 1: SUBMITTING EXPORT TASKS TO ZTE EPMS API...")
    print("========================================================")

    for project_key, project_info in auth.get("projects", {}).items():
        project_id = project_info.get("projId")
        if not project_id or "PASTE" in project_id:
            print(f"Skipping project {project_key}: projId not configured.")
            continue
        if project_key not in project_configs:
            continue

        headers = base_headers.copy()
        headers["X-Itp-Value"] = f"timeZone=8;projId={project_id}"
        project_cookies = cookies.copy()
        project_cookies["projId"] = project_id

        for pattern, file_config in project_configs[project_key]["files"].items():
            clean_name = file_config["clean_name"]
            payload = {
                "clusterIdList": [],
                "fieldQueryDTOList": [],
                "phaseIdList": [],
                "regionIdList": [],
                "siteKeyList": [],
                "duCode": "",
                "duName": "",
                "duModelId": file_config["duModelId"],
                "duStatus": "ENABLED",
                "pageNum": 1,
                "pageSize": 20,
                "searchType": "HIGH",
                "viewId": file_config["viewId"],
            }

            print(f"  Submitting export task for '{pattern}' (Project: {project_key})...")
            try:
                response = requests_module.post(
                    EXPORT_URL,
                    headers=headers,
                    cookies=project_cookies,
                    json=payload,
                    timeout=30,
                )
                if response.status_code == 200:
                    print("    -> Export task submitted successfully.")
                else:
                    print(
                        f"    -> Warning: Export submission failed (HTTP {response.status_code}). "
                        "Polling recent export records."
                    )
            except Exception as exc:
                print(f"    -> Error submitting export task: {exc}. Polling recent export records.")

            pending_files[clean_name] = {
                "pat": pattern,
                "proj_key": project_key,
                "projId": project_id,
                "headers": headers,
                "cookies": project_cookies,
            }

    return pending_files


def _bounded_timeout(window: PollWindow, maximum_seconds: float) -> float:
    remaining = window.remaining()
    if remaining <= 0:
        return 0.0
    return min(float(maximum_seconds), remaining)


def _poll_pending_files(
    pending_files: Dict[str, dict],
    *,
    input_dir: str,
    script_start_time: datetime.datetime,
    timeout_seconds: int,
    interval_seconds: int,
    requests_module,
    monotonic: Optional[Callable[[], float]] = None,
    sleeper: Optional[Callable[[float], None]] = None,
) -> bool:
    window_kwargs = {}
    if monotonic is not None:
        window_kwargs["monotonic"] = monotonic
    if sleeper is not None:
        window_kwargs["sleeper"] = sleeper
    window = PollWindow(timeout_seconds, interval_seconds, **window_kwargs)
    failed_files = []

    print("\n========================================================")
    print("STEP 2: POLLING AND DOWNLOADING GENERATED EXCEL SHEETS...")
    print("========================================================")

    while pending_files and not window.expired():
        emit_run_state("POLLING", **window.snapshot(pending_files.keys()))
        window.sleep()
        if window.expired():
            break

        projects_to_query: Dict[str, dict] = {}
        for clean_name, info in list(pending_files.items()):
            project_id = info["projId"]
            project = projects_to_query.setdefault(
                project_id,
                {"headers": info["headers"], "cookies": info["cookies"], "files": []},
            )
            project["files"].append(clean_name)

        for project_id, project_data in projects_to_query.items():
            record_timeout = _bounded_timeout(window, 30)
            if record_timeout <= 0:
                break
            params = {
                "operationType": "EXPORT",
                "pageNo": "1",
                "pageSize": "20",
                "bizType": "SCHEDULE",
            }
            try:
                response = requests_module.get(
                    RECORD_URL,
                    headers=project_data["headers"],
                    cookies=project_data["cookies"],
                    params=params,
                    timeout=record_timeout,
                )
                if window.expired():
                    break
                if response.status_code != 200:
                    continue
                body = response.json().get("bo")
                rows = body.get("rows", []) if body else []

                for clean_name in list(project_data["files"]):
                    if window.expired():
                        break
                    info = pending_files.get(clean_name)
                    if info is None:
                        continue
                    pattern = info["pat"]
                    matched_row = None
                    for row in rows:
                        file_name = row.get("fileName") or ""
                        submitted = row.get("submitDate")
                        recent = False
                        if submitted:
                            try:
                                submitted_at = datetime.datetime.strptime(
                                    submitted, "%Y-%m-%d %H:%M:%S"
                                )
                                recent = submitted_at >= (
                                    script_start_time - datetime.timedelta(minutes=3)
                                )
                            except ValueError:
                                recent = False
                        if pattern in file_name and recent:
                            matched_row = row
                            break

                    if not matched_row:
                        continue
                    status = matched_row.get("status")
                    progress = matched_row.get("schedule")
                    ticket = matched_row.get("operationNo")
                    if status == "SUCCESS" and progress == 100:
                        download_timeout = _bounded_timeout(window, 60)
                        if download_timeout <= 0:
                            break
                        print(f"  [READY] '{pattern}' is complete (Ticket: {ticket}). Downloading...")
                        params = {
                            "docId": matched_row.get("fileId"),
                            "fileName": matched_row.get("fileName"),
                        }
                        output_path = os.path.join(input_dir, f"{clean_name}.xlsx")
                        try:
                            with requests_module.get(
                                DOWNLOAD_URL,
                                headers=project_data["headers"],
                                cookies=project_data["cookies"],
                                params=params,
                                stream=True,
                                timeout=download_timeout,
                            ) as download:
                                download.raise_for_status()
                                with open(output_path, "wb") as output:
                                    for chunk in download.iter_content(chunk_size=8192):
                                        output.write(chunk)
                            if window.expired():
                                try:
                                    os.remove(output_path)
                                except FileNotFoundError:
                                    pass
                                break
                            print(f"    -> SUCCESS: Saved {clean_name}.xlsx")
                            del pending_files[clean_name]
                        except Exception as exc:
                            print(f"    -> Download failed: {exc}")
                    elif status in ("FAIL", "ERROR"):
                        print(f"  [FAILED] '{pattern}' failed on server.")
                        failed_files.append(clean_name)
                        del pending_files[clean_name]
                    else:
                        print(f"  [ONGOING] '{pattern}' is still generating on server ({progress}%).")
            except Exception as exc:
                print(f"  Error polling records for project ID {project_id}: {exc}")

    if pending_files:
        emit_run_state("POLLING", **window.snapshot(pending_files.keys()))
        print("\nWarning: The following files timed out or failed to export:")
        for clean_name in pending_files:
            print(f"  - {clean_name}")
        return False
    if failed_files:
        print("\nWarning: The following files failed on the export server:")
        for clean_name in failed_files:
            print(f"  - {clean_name}")
        return False

    print("\nAll files successfully downloaded!")
    return True


def fetch_latest_exports(
    script_dir: str,
    input_dir: str,
    *,
    fetch_timeout_seconds: int = 600,
    poll_interval_seconds: int = 5,
    requests_module=None,
    auth_server: Optional[Callable[[str], None]] = None,
    monotonic: Optional[Callable[[], float]] = None,
    sleeper: Optional[Callable[[float], None]] = None,
) -> bool:
    selected_requests = requests_module or requests
    if selected_requests is None:
        raise RuntimeError("requests is required for live IEPMS export")

    project_configs, legacy_auth_server = _legacy_components()
    selected_auth_server = auth_server or legacy_auth_server
    os.makedirs(input_dir, exist_ok=True)
    script_start_time = datetime.datetime.now()
    auth = _ensure_auth(
        script_dir,
        requests_module=selected_requests,
        auth_server=selected_auth_server,
    )
    pending_files = _submit_exports(auth, project_configs, selected_requests)
    if not pending_files:
        print("Warning: No export tasks were configured or submitted.")
        return False

    return _poll_pending_files(
        pending_files,
        input_dir=input_dir,
        script_start_time=script_start_time,
        timeout_seconds=fetch_timeout_seconds,
        interval_seconds=poll_interval_seconds,
        requests_module=selected_requests,
        monotonic=monotonic,
        sleeper=sleeper,
    )
