import os
import csv
import re
import json
import argparse
import datetime
import warnings
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# Suppress harmless openpyxl stylesheet warnings
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

try:
    import pandas as pd
    import requests
except ImportError:
    pd = None
    requests = None

# Manually verified column mappings for the 6 clean CSV files
VERIFIED_MAPPINGS = {
    "2023_TX_Rollout.csv": {
        "SOW": 82,
        "TSS": 132,
        "MC": 205,
        "MOS": 211,
        "TI": 217,
        "L1": 325,
        "RFS": 230,
        "PAC": 310
    },
    "2024_Celcomdigi_BAU.csv": {
        "SOW": 182,
        "TSS": 47,
        "MC": 51,
        "MOS": None,
        "TI": 250,
        "L1": 53,
        "RFS": 163,
        "PAC": 73
    },
    "Jendela_TX_Migration.csv": {
        "SOW": 538,
        "TSS": 14,
        "MC": 64,
        "MOS": 78,
        "TI": 92,
        "L1": 311,
        "RFS": 143,
        "PAC": 281
    },
    "TX_Mini_Project.csv": {
        "SOW": 250,
        "TSS": 70,
        "MC": 96,
        "MOS": 101,
        "TI": 107,
        "L1": 128,
        "RFS": 119,
        "PAC": 222
    },
    "MW_EOS_Swap.csv": {
        "SOW": 248,
        "TSS": 110,
        "MC": 140,
        "MOS": 145,
        "TI": 156,
        "L1": 162,
        "RFS": 167,
        "PAC": 233
    },
    "ZTE_TX_MINI.csv": {
        "SOW": 10,
        "TSS": 43,
        "MC": 109,
        "MOS": 112,
        "TI": 115,
        "L1": 127,
        "RFS": 118,
        "PAC": 148
    }
}

# Milestone search keywords configuration (used for auto-detect of unknown sheets)
MILESTONE_KEYWORDS = {
    "SOW": {
        "primary": ["tx planning", "sow", "scope of work"],
        "stage": ["tx planning", "commercial", "planner"]
    },
    "TSS": {
        "primary": ["physical survey", "tssr customer approval", "tssr submitted to customer", "e-tss"],
        "stage": ["survey", "design", "rollout", "etss"]
    },
    "MC": {
        "primary": ["material collection", "material collect"],
        "stage": ["ready for installation", "warehouse", "installation"]
    },
    "MOS": {
        "primary": ["material on site", "material on-site"],
        "stage": ["material on site", "rollout", "warehouse"]
    },
    "TI": {
        "primary": ["equipment installation", "telecom installation", "equipment install"],
        "stage": ["telecom installation", "rollout", "installation"]
    },
    "L1": {
        "primary": ["l1 approved", "l1 report", "line 1"],
        "stage": ["q&ehs", "pac site binder complete"]
    },
    "RFS": {
        "primary": ["site integrated", "tx integrated", "tx integration end date", "cut-over end date", "cutover"],
        "stage": ["software commissioning", "operation", "installation"]
    },
    "PAC": {
        "primary": ["pac approved", "preliminary acceptance certification", "provisional acceptance"],
        "stage": ["preliminary/provisional", "acceptance certification", "pac work complete"]
    }
}

# Static view IDs and model IDs for triggering export tasks
PROJECT_CONFIGS = {
    "Malaysia_CelcomDigi_Project": {
        "projId": "c46633e8-6e52-2178-f17e-dcbfdade7cb2",
        "files": {
            "2023 TX Rollout": {
                "clean_name": "2023_TX_Rollout",
                "duModelId": "1027190858144623081",
                "viewId": "8043814649254951526"
            },
            "2024 Celcomdigi BAU": {
                "clean_name": "2024_Celcomdigi_BAU",
                "duModelId": "7278317398457076992",
                "viewId": "4729280009710993817"
            },
            "Jendela TX Migration": {
                "clean_name": "Jendela_TX_Migration",
                "duModelId": "4972593269368006257",
                "viewId": "6638925130999114751"
            },
            "TX Mini Project": {
                "clean_name": "TX_Mini_Project",
                "duModelId": "4188808420049567786",
                "viewId": "2540490949868649705"
            }
        }
    },
    "CelcomDigi_MW": {
        "projId": "59e45f77-a828-6fa5-1701-dd6c4427df9d",
        "files": {
            "MW EOS Swap": {
                "clean_name": "MW_EOS_Swap",
                "duModelId": "5440935430300168497",
                "viewId": "7476572371505372260"
            },
            "ZTE TX MINI": {
                "clean_name": "ZTE_TX_MINI",
                "duModelId": "8638668101234290847",
                "viewId": "2279585426760368522"
            }
        }
    }
}

class AuthSyncHandler(BaseHTTPRequestHandler):
    script_dir = None
    server_instance = None
    
    def log_message(self, format, *args):
        # Suppress logging HTTP requests to keep terminal clean
        return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        if self.path == "/sync":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                auth_path = os.path.join(self.script_dir, "api_auth.json")
                auth_data = {}
                if os.path.exists(auth_path):
                    with open(auth_path, 'r', encoding='utf-8') as f:
                        auth_data = json.load(f)
                
                auth_data["cookie"] = post_data
                auth_data["x_auth_value"] = "" # Automatically extracted in next run
                auth_data["x_emp_no"] = "10265696"
                
                if "projects" not in auth_data:
                    auth_data["projects"] = {
                        "Malaysia_CelcomDigi_Project": { "projId": "c46633e8-6e52-2178-f17e-dcbfdade7cb2" },
                        "CelcomDigi_MW": { "projId": "59e45f77-a828-6fa5-1701-dd6c4427df9d" }
                    }
                    
                with open(auth_path, 'w', encoding='utf-8') as f:
                    json.dump(auth_data, f, indent=4)
                    
                # Respond with CORS headers
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
                
                print("\n[SUCCESS] Authentication cookies synchronized successfully!")
                self.server_instance.keep_running = False
                
            except Exception as e:
                self.send_response(500)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))

def run_auth_server(script_dir):
    class BindedHandler(AuthSyncHandler):
        pass
    BindedHandler.script_dir = script_dir
    
    server = HTTPServer(('localhost', 18290), BindedHandler)
    BindedHandler.server_instance = server
    server.keep_running = True
    
    print("\n=========================================================================")
    print("🔑 AUTOMATIC AUTHENTICATION SYNC REQUIRED")
    print("=========================================================================")
    print("Your login session is expired or missing.")
    print("A temporary local sync server has started on: http://localhost:18290")
    print("\n👉 How to Sync in 1 Click:")
    print("1. Open the ZTE IEPMS page in your browser.")
    print("2. Click your 'Sync Auth' bookmarklet on your bookmarks bar.")
    print("\n   Bookmarklet Code (copy & save as bookmark URL):")
    print("   javascript:(async()=>{try{const r=await fetch('http://localhost:18290/sync',{method:'POST',body:document.cookie});const d=await r.json();if(d.status==='success')alert('🔒 ZTE EPMS Auth Sync Successful! Check your terminal.');else alert('❌ Sync Failed.');}catch(e){alert('❌ Could not connect. Run the python script first!');}})()")
    print("=========================================================================\n")
    print("Waiting for sync request...")
    
    while server.keep_running:
        server.handle_request()

def format_excel_cell(val):
    """
    Cleans cell data for identical output structure (keeps date formatting cleanly as YYYY-MM-DD)
    """
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.strftime('%Y-%m-%d')
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    if isinstance(val, str) and val.endswith(' 00:00:00'):
        return val[:-9]
    if pd and pd.isna(val):
        return ""
    return str(val)

def convert_xlsx_to_csv(xlsx_path, csv_path):
    """
    Converts a single .xlsx file to a UTF-8 CSV with identical formatting.
    """
    if pd is None:
        print("Error: pandas and openpyxl are required for Excel conversion.")
        return False
    try:
        df = pd.read_excel(xlsx_path, sheet_name=0, header=None)
        if hasattr(df, 'map'):
            df = df.map(format_excel_cell)
        else:
            df = df.applymap(format_excel_cell)
        df.to_csv(csv_path, index=False, header=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        print(f"Failed to convert {os.path.basename(xlsx_path)}: {e}")
        return False

def check_and_convert_all_xlsx(input_dir, force_convert=False):
    if pd is None:
        return
        
    xlsx_files = [f for f in os.listdir(input_dir) if f.endswith('.xlsx') and "test" not in f]
    if not xlsx_files:
        return
        
    print("Checking Excel (.xlsx) files in input directory...")
    for xlsx_file in xlsx_files:
        xlsx_path = os.path.join(input_dir, xlsx_file)
        csv_file = xlsx_file.rsplit('.', 1)[0] + '.csv'
        csv_path = os.path.join(input_dir, csv_file)
        
        should_convert = force_convert or not os.path.exists(csv_path)
        
        if not should_convert:
            xlsx_time = os.path.getmtime(xlsx_path)
            csv_time = os.path.getmtime(csv_path)
            if xlsx_time > csv_time:
                should_convert = True
                
        if should_convert:
            print(f"  -> Converting: {xlsx_file} -> {csv_file} (This may take a moment for large files)...")
            success = convert_xlsx_to_csv(xlsx_path, csv_path)
            if success:
                print("     SUCCESS")

def auto_detect_mappings(input_dir):
    csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv') and "test" not in f]
    detected_mappings = {}

    for f in csv_files:
        path = os.path.join(input_dir, f)
        try:
            with open(path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                headers = []
                for _ in range(4):
                    row = next(reader, None)
                    if row is not None:
                        headers.append(row)
                
                if not headers:
                    continue
                
                num_cols = len(headers[0])
                detected_mappings[f] = {}
                
                for ms, kw_info in MILESTONE_KEYWORDS.items():
                    best_col = None
                    best_score = -1
                    
                    for col_idx in range(num_cols):
                        col_headers = [headers[r_idx][col_idx] for r_idx in range(len(headers)) if col_idx < len(headers[r_idx])]
                        col_str = " | ".join(col_headers).lower()
                        
                        is_actual_end = ("end" in col_str or "actual" in col_str or "date" in col_str) and \
                                         ("start" not in col_str) and \
                                         ("plan month" not in col_str) and \
                                         ("plan week" not in col_str)
                        if not is_actual_end:
                            continue
                        
                        score = 0
                        for pk in kw_info["primary"]:
                            if pk in col_str:
                                score += 10
                        for sk in kw_info["stage"]:
                            if sk in col_str:
                                score += 2
                                
                        if score > best_score and score >= 2:
                            best_score = score
                            best_col = col_idx
                            
                    detected_mappings[f][ms] = best_col
                    
        except Exception as e:
            print(f"Warning: Failed to auto-detect mappings for {f}: {e}")
            
    return detected_mappings

def parse_year_month(val, target_year):
    val = val.strip()
    if not val:
        return None
    years = re.findall(r'\b\d{4}\b', val)
    if str(target_year) not in years:
        return None
    parts = re.split(r'[-/]', val)
    if len(parts) >= 2:
        if len(parts[0]) == 4:
            return int(parts[1])
        elif len(parts[-1]) == 4:
            return int(parts[1])
    return None

def parse_date_only(val):
    val = val.strip()
    if not val or val.lower() in ["null", "none"]:
        return None
    # Try different formats
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S', '%Y/%m/%d %H:%M:%S'):
        try:
            return datetime.datetime.strptime(val, fmt).date()
        except ValueError:
            pass
    # Try extracting YYYY-MM-DD using regex
    m = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', val)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    return None

def format_sla_row(kpi_name, stats):
    met = stats["met"]
    warn = stats["warn"]
    breached = stats["breached"]
    total_open = met + warn + breached
    
    if total_open > 0:
        compliance = ((met + warn) / total_open) * 100
        avg_days = stats["total_days"] / total_open
        compliance_str = f"**{compliance:.1f}%**"
        avg_days_str = f"{avg_days:.1f}"
    else:
        compliance_str = "N/A"
        avg_days_str = "N/A"
        
    return f"| {kpi_name} | {total_open} | {met} | {warn} | {breached} | {compliance_str} | {avg_days_str} |"

def execute_api_fetch_workflow(script_dir, input_dir):
    script_start_time = datetime.datetime.now()
    auth_path = os.path.join(script_dir, "api_auth.json")
    if not os.path.exists(auth_path):
        run_auth_server(script_dir)
        
    # Load and parse cookies
    with open(auth_path, 'r', encoding='utf-8') as f:
        auth = json.load(f)

    cookie_str = auth.get("cookie", "")
    cookies = {}
    for item in cookie_str.split(";"):
        if "=" in item:
            k, v = item.strip().split("=", 1)
            cookies[k] = v

    # Validate auth token exists and test connectivity
    x_auth = auth.get("x_auth_value", "")
    if not x_auth or "YOUR_AUTH_VALUE" in x_auth:
        x_auth = cookies.get("ZTEDPGSSOCookie", cookies.get("UCSSSOToken", ""))

    test_headers = {
        'Accept': 'application/json',
        'X-Auth-Value': x_auth,
        'X-Emp-No': auth.get("x_emp_no", "10265696"),
        'X-Lang-Id': 'en_US',
        'X-Org-Id': '1',
        'X-Tenant-Id': '10001',
        'Internal': '1'
    }
    
    test_params = {'operationType': 'EXPORT', 'pageNo': '1', 'pageSize': '1', 'bizType': 'SCHEDULE'}
    record_url = "https://iepms.zte.com.cn/zte-crm-iepms-basebff/zte-crm-iepms-schedule/record"
    
    # Try connectivity
    try:
        r = requests.get(record_url, headers=test_headers, cookies=cookies, params=test_params, timeout=10)
        # Check if auth failed (non-200 or indicates unauthorized error in JSON)
        is_unauthorized = r.status_code != 200
        if r.status_code == 200:
            resp_json = r.json()
            ret_code = resp_json.get("code", {}).get("code", "")
            if ret_code != "0000":
                is_unauthorized = True
                
        if is_unauthorized:
            print("Authentication token is expired or unauthorized.")
            run_auth_server(script_dir)
            # Reload auth data after sync
            with open(auth_path, 'r', encoding='utf-8') as f:
                auth = json.load(f)
    except Exception as e:
        print(f"Connectivity test failed: {e}. Will attempt to start auth sync server.")
        run_auth_server(script_dir)
        with open(auth_path, 'r', encoding='utf-8') as f:
            auth = json.load(f)

    # 1. Prepare finalized headers and cookies
    cookie_str = auth.get("cookie", "")
    cookies = {}
    for item in cookie_str.split(";"):
        if "=" in item:
            k, v = item.strip().split("=", 1)
            cookies[k] = v

    x_auth = auth.get("x_auth_value", "")
    if not x_auth or "YOUR_AUTH_VALUE" in x_auth:
        x_auth = cookies.get("ZTEDPGSSOCookie", cookies.get("UCSSSOToken", ""))

    base_headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6,ms;q=0.5',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Internal': '1',
        'Referer': 'https://iepms.zte.com.cn/zte-crm-iepms-scheduleui/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
        'X-Auth-Value': x_auth,
        'X-Emp-No': auth.get("x_emp_no", "10265696"),
        'X-Lang-Id': 'en_US',
        'X-Org-Id': '1',
        'X-Origin-ServiceName': 'zte-crm-iepms-schedule',
        'X-Target-ServiceName': 'zte-crm-iepms-schedule',
        'X-Tenant-Id': '10001'
    }

    export_url = "https://iepms.zte.com.cn/zte-crm-iepms-basebff/zte-crm-iepms-schedule/schedule/export"
    download_url = "https://iepms.zte.com.cn/zte-crm-iepms-basebff/zte-crm-iepms-schedule/record/download"
    
    pending_files = {}
    
    print("\n========================================================")
    print("STEP 1: SUBMITTING EXPORT TASKS TO ZTE EPMS API...")
    print("========================================================")
    
    for proj_key, proj_info in auth.get("projects", {}).items():
        proj_id = proj_info.get("projId")
        if not proj_id or "PASTE" in proj_id:
            print(f"Skipping project {proj_key}: projId not configured.")
            continue
            
        if proj_key not in PROJECT_CONFIGS:
            continue
            
        static_proj = PROJECT_CONFIGS[proj_key]
        headers = base_headers.copy()
        headers['X-Itp-Value'] = f'timeZone=8;projId={proj_id}'
        cookies_context = cookies.copy()
        cookies_context['projId'] = proj_id
        
        for pat, file_cfg in static_proj["files"].items():
            clean_name = file_cfg["clean_name"]
            du_model_id = file_cfg["duModelId"]
            view_id = file_cfg["viewId"]
            
            payload = {
                "clusterIdList": [],
                "fieldQueryDTOList": [],
                "phaseIdList": [],
                "regionIdList": [],
                "siteKeyList": [],
                "duCode": "",
                "duName": "",
                "duModelId": du_model_id,
                "duStatus": "ENABLED",
                "pageNum": 1,
                "pageSize": 20,
                "searchType": "HIGH",
                "viewId": view_id
            }
            
            print(f"  Submitting export task for '{pat}' (Project: {proj_key})...")
            try:
                response = requests.post(export_url, headers=headers, cookies=cookies_context, json=payload, timeout=30)
                if response.status_code == 200:
                    print(f"    -> Export task submitted successfully.")
                    pending_files[clean_name] = {
                        "pat": pat,
                        "proj_key": proj_key,
                        "projId": proj_id,
                        "headers": headers,
                        "cookies": cookies_context
                    }
                else:
                    print(f"    -> Warning: Export submission failed (HTTP {response.status_code}). Will try polling latest historical file.")
                    pending_files[clean_name] = {
                        "pat": pat,
                        "proj_key": proj_key,
                        "projId": proj_id,
                        "headers": headers,
                        "cookies": cookies_context
                    }
            except Exception as e:
                print(f"    -> Error submitting export task: {e}. Will attempt historical backup.")
                pending_files[clean_name] = {
                    "pat": pat,
                    "proj_key": proj_key,
                    "projId": proj_id,
                    "headers": headers,
                    "cookies": cookies_context
                }

    print("\n========================================================")
    print("STEP 2: POLLING AND DOWNLOADING GENERATED EXCEL SHEETS...")
    print("========================================================")
    
    max_polls = 24
    poll_interval = 5
    
    for attempt in range(max_polls):
        if not pending_files:
            break
            
        print(f"\nPolling attempt {attempt + 1}/{max_polls} (waiting for {len(pending_files)} files)...")
        time.sleep(poll_interval)
        
        projects_to_query = {}
        for clean_name, info in list(pending_files.items()):
            proj_id = info["projId"]
            if proj_id not in projects_to_query:
                projects_to_query[proj_id] = {
                    "headers": info["headers"],
                    "cookies": info["cookies"],
                    "files": []
                }
            projects_to_query[proj_id]["files"].append(clean_name)
            
        for proj_id, proj_data in projects_to_query.items():
            params = {
                'operationType': 'EXPORT',
                'pageNo': '1',
                'pageSize': '20',
                'bizType': 'SCHEDULE'
            }
            
            try:
                rec_resp = requests.get(record_url, headers=proj_data["headers"], cookies=proj_data["cookies"], params=params, timeout=30)
                if rec_resp.status_code != 200:
                    continue
                    
                bo_data = rec_resp.json().get("bo")
                rows = bo_data.get("rows", []) if bo_data else []
                
                for clean_name in list(proj_data["files"]):
                    info = pending_files[clean_name]
                    pat = info["pat"]
                    
                    matched_row = None
                    for row in rows:
                        file_name = row.get("fileName") or ""
                        submit_date_str = row.get("submitDate")
                        
                        is_recent = False
                        if submit_date_str:
                            try:
                                submit_dt = datetime.datetime.strptime(submit_date_str, "%Y-%m-%d %H:%M:%S")
                                if submit_dt >= (script_start_time - datetime.timedelta(minutes=3)):
                                    is_recent = True
                            except ValueError:
                                pass
                                
                        if pat in file_name and is_recent:
                            matched_row = row
                            break
                            
                    if matched_row:
                        status = matched_row.get("status")
                        progress = matched_row.get("schedule")
                        ticket = matched_row.get("operationNo")
                        
                        if status == "SUCCESS" and progress == 100:
                            file_id = matched_row.get("fileId")
                            real_file_name = matched_row.get("fileName")
                            print(f"  [READY] '{pat}' is complete (Ticket: {ticket}). Downloading...")
                            
                            dl_params = {'docId': file_id, 'fileName': real_file_name}
                            out_path = os.path.join(input_dir, f"{clean_name}.xlsx")
                            
                            try:
                                with requests.get(download_url, headers=proj_data["headers"], cookies=proj_data["cookies"], params=dl_params, stream=True, timeout=60) as r:
                                    r.raise_for_status()
                                    with open(out_path, 'wb') as f_out:
                                        for chunk in r.iter_content(chunk_size=8192):
                                            f_out.write(chunk)
                                print(f"    -> SUCCESS: Saved {clean_name}.xlsx")
                                del pending_files[clean_name]
                            except Exception as e:
                                print(f"    -> Download failed: {e}")
                        elif status in ["FAIL", "ERROR"]:
                            print(f"  [FAILED] '{pat}' failed on server. Removing from auto-download queue.")
                            del pending_files[clean_name]
                        else:
                            print(f"  [ONGOING] '{pat}' is still generating on server ({progress}%).")
                            
            except Exception as e:
                print(f"  Error polling records for project ID {proj_id}: {e}")
                
    if pending_files:
        print("\nWarning: The following files timed out or failed to export:")
        for clean_name in pending_files:
            print(f"  - {clean_name}")
        return False
        
    print("\nAll files successfully downloaded!")
    return True

def main():
    # Resolve project root dynamically (parent of scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir) if os.path.basename(script_dir).lower() == "scripts" else script_dir

    # Restructured default folders
    default_input_dir = os.path.join(project_root, "input")
    default_output_dir = os.path.join(project_root, "output")
    default_docs_dir = os.path.join(project_root, "docs")

    parser = argparse.ArgumentParser(description="IEPMS Transmission Milestone Progress Analyzer")
    parser.add_argument("--input-dir", default=default_input_dir, help="Directory containing the input CSV/Excel files")
    parser.add_argument("--output-dir", default=default_output_dir, help="Directory to save output reports")
    parser.add_argument("--docs-dir", default=default_docs_dir, help="Directory to save column mappings documentation")
    parser.add_argument("--year", type=int, default=2026, help="Target year for analysis")
    parser.add_argument("--config", default="milestone_config.json", help="Filename of the JSON config mappings")
    parser.add_argument("--output-report", default="Milestone_Progress_Report_{year}.md", help="Output report filename")
    parser.add_argument("--output-mappings", default="milestone_mappings.md", help="Output mapping documentation filename")
    parser.add_argument("--force-detect", action="store_true", help="Force auto-detection and overwrite config file")
    parser.add_argument("--force-convert", action="store_true", help="Force conversion of all .xlsx files to .csv")
    parser.add_argument("--no-convert", action="store_true", help="Disable automatic .xlsx to .csv conversion check")
    parser.add_argument("--fetch", action="store_true", help="Fetch the latest Excel sheets from the API before analyzing")
    
    args = parser.parse_args()
    
    input_dir = args.input_dir
    output_dir = args.output_dir
    docs_dir = args.docs_dir
    target_year = args.year
    
    # Configuration remains in the scripts directory alongside the python script
    config_path = os.path.join(script_dir, args.config)
    
    # Reports and mappings output paths are resolved using the respective directories
    output_report = os.path.join(output_dir, args.output_report.format(year=target_year))
    output_mappings = os.path.join(docs_dir, args.output_mappings)
    
    # Create output directories if they don't exist
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(docs_dir, exist_ok=True)
    
    # 0. Fetch Excel files from API if requested
    if args.fetch:
        success = execute_api_fetch_workflow(script_dir, input_dir)
        if not success:
            print("Warning: API fetch failed or was incomplete. Continuing with existing files.")
    
    # 1. Run Excel to CSV check
    if not args.no_convert:
        check_and_convert_all_xlsx(input_dir, force_convert=args.force_convert)
    
    # 2. Load or generate mappings config
    mappings = {}
    if os.path.exists(config_path) and not args.force_detect:
        print(f"Loading milestone mapping configuration from: {config_path}")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
        except Exception as e:
            print(f"Error loading config, falling back to database/auto-detection: {e}")
            mappings = {}
            
    if not mappings:
        # Check files in input directory
        csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv') and "test" not in f]
        
        # Populate mapping: first use verified mappings, fallback to auto-detect for unknown files
        for f in csv_files:
            if f in VERIFIED_MAPPINGS and not args.force_detect:
                mappings[f] = VERIFIED_MAPPINGS[f]
            else:
                # Run auto-detect for this single file
                single_detect = auto_detect_mappings(input_dir)
                if f in single_detect:
                    mappings[f] = single_detect[f]
        
        # Save mapping configuration to scripts directory
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, indent=4)
            print(f"Saved mapping configuration to: {config_path}")
        except Exception as e:
            print(f"Warning: Could not save config file: {e}")
            
    # 3. Process CSV files and extract stats
    milestones = ["SOW", "TSS", "MC", "MOS", "TI", "L1", "RFS", "PAC"]
    file_stats = {}
    combined_stats = {ms: {m: 0 for m in range(1, 13)} for ms in milestones}
    mappings_metadata = {}
    today = datetime.date.today()
    
    file_sla_stats = {}
    combined_sla_stats = {
        "MC_MOS": {"met": 0, "warn": 0, "breached": 0, "pending": 0, "total_days": 0, "count": 0},
        "TI_L1": {"met": 0, "warn": 0, "breached": 0, "pending": 0, "total_days": 0, "count": 0},
        "MC_PAC": {"met": 0, "warn": 0, "breached": 0, "pending": 0, "total_days": 0, "count": 0}
    }
    
    csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv') and f in mappings and "test" not in f]
    
    for f in csv_files:
        path = os.path.join(input_dir, f)
        # Extract friendly name
        friendly_name = f.replace('_', ' ').replace('.csv', '')
        
        file_stats[friendly_name] = {ms: {m: 0 for m in range(1, 13)} for ms in milestones}
        mappings_metadata[friendly_name] = {}
        
        file_sla_stats[friendly_name] = {
            "MC_MOS": {"met": 0, "warn": 0, "breached": 0, "pending": 0, "total_days": 0, "count": 0},
            "TI_L1": {"met": 0, "warn": 0, "breached": 0, "pending": 0, "total_days": 0, "count": 0},
            "MC_PAC": {"met": 0, "warn": 0, "breached": 0, "pending": 0, "total_days": 0, "count": 0}
        }
        
        try:
            with open(path, 'r', encoding='utf-8') as file:
                reader = list(csv.reader(file))
                headers = reader[:4]
                data_rows = reader[4:]
                
                for ms in milestones:
                    col_idx = mappings[f].get(ms)
                    if col_idx is None:
                        mappings_metadata[friendly_name][ms] = {
                            "col_idx": "N/A", "header_0": "N/A", "header_1": "N/A", "header_2": "N/A", "header_3": "N/A"
                        }
                        continue
                    
                    col_headers = [headers[r_idx][col_idx] for r_idx in range(len(headers)) if col_idx < len(headers[r_idx])]
                    mappings_metadata[friendly_name][ms] = {
                        "col_idx": col_idx,
                        "header_0": col_headers[0] if len(col_headers) > 0 else "",
                        "header_1": col_headers[1] if len(col_headers) > 1 else "",
                        "header_2": col_headers[2] if len(col_headers) > 2 else "",
                        "header_3": col_headers[3] if len(col_headers) > 3 else ""
                    }
                    
                    for row in data_rows:
                        if col_idx < len(row):
                            val = row[col_idx].strip()
                            m = parse_year_month(val, target_year)
                            if m and 1 <= m <= 12:
                                file_stats[friendly_name][ms][m] += 1
                                combined_stats[ms][m] += 1
                                
                # SLA processing for this project
                mc_col = mappings[f].get("MC")
                mos_col = mappings[f].get("MOS")
                ti_col = mappings[f].get("TI")
                l1_col = mappings[f].get("L1")
                pac_col = mappings[f].get("PAC")
                
                for row in data_rows:
                    mc_date = parse_date_only(row[mc_col]) if mc_col is not None and mc_col < len(row) else None
                    mos_date = parse_date_only(row[mos_col]) if mos_col is not None and mos_col < len(row) else None
                    ti_date = parse_date_only(row[ti_col]) if ti_col is not None and ti_col < len(row) else None
                    l1_date = parse_date_only(row[l1_col]) if l1_col is not None and l1_col < len(row) else None
                    pac_date = parse_date_only(row[pac_col]) if pac_col is not None and pac_col < len(row) else None
                    
                    # MC -> MOS
                    if mc_date and not mos_date and mc_date.year == target_year:
                        dur = (today - mc_date).days
                        if dur < 0:
                            dur = 0
                        file_sla_stats[friendly_name]["MC_MOS"]["total_days"] += dur
                        file_sla_stats[friendly_name]["MC_MOS"]["count"] += 1
                        combined_sla_stats["MC_MOS"]["total_days"] += dur
                        combined_sla_stats["MC_MOS"]["count"] += 1
                        
                        if dur < 10:
                            file_sla_stats[friendly_name]["MC_MOS"]["met"] += 1
                            combined_sla_stats["MC_MOS"]["met"] += 1
                        elif dur <= 13:
                            file_sla_stats[friendly_name]["MC_MOS"]["warn"] += 1
                            combined_sla_stats["MC_MOS"]["warn"] += 1
                        else:
                            file_sla_stats[friendly_name]["MC_MOS"]["breached"] += 1
                            combined_sla_stats["MC_MOS"]["breached"] += 1
                            
                    # TI -> L1
                    if ti_date and not l1_date and ti_date.year == target_year:
                        dur = (today - ti_date).days
                        if dur < 0:
                            dur = 0
                        file_sla_stats[friendly_name]["TI_L1"]["total_days"] += dur
                        file_sla_stats[friendly_name]["TI_L1"]["count"] += 1
                        combined_sla_stats["TI_L1"]["total_days"] += dur
                        combined_sla_stats["TI_L1"]["count"] += 1
                        
                        if dur < 10:
                            file_sla_stats[friendly_name]["TI_L1"]["met"] += 1
                            combined_sla_stats["TI_L1"]["met"] += 1
                        elif dur <= 13:
                            file_sla_stats[friendly_name]["TI_L1"]["warn"] += 1
                            combined_sla_stats["TI_L1"]["warn"] += 1
                        else:
                            file_sla_stats[friendly_name]["TI_L1"]["breached"] += 1
                            combined_sla_stats["TI_L1"]["breached"] += 1
                            
                    # MC -> PAC
                    if mc_date and not pac_date and mc_date.year == target_year:
                        dur = (today - mc_date).days
                        if dur < 0:
                            dur = 0
                        file_sla_stats[friendly_name]["MC_PAC"]["total_days"] += dur
                        file_sla_stats[friendly_name]["MC_PAC"]["count"] += 1
                        combined_sla_stats["MC_PAC"]["total_days"] += dur
                        combined_sla_stats["MC_PAC"]["count"] += 1
                        
                        if dur < 25:
                            file_sla_stats[friendly_name]["MC_PAC"]["met"] += 1
                            combined_sla_stats["MC_PAC"]["met"] += 1
                        elif dur <= 29:
                            file_sla_stats[friendly_name]["MC_PAC"]["warn"] += 1
                            combined_sla_stats["MC_PAC"]["warn"] += 1
                        else:
                            file_sla_stats[friendly_name]["MC_PAC"]["breached"] += 1
                            combined_sla_stats["MC_PAC"]["breached"] += 1
                                
        except Exception as e:
            print(f"Error processing file {f}: {e}")
            
    # Generate Output 1: docs/milestone_mappings.md
    with open(output_mappings, 'w', encoding='utf-8') as f:
        f.write("# Project Milestone vs Column Header Mappings\n\n")
        f.write("This document defines the column header mappings used to extract milestone completion dates across all projects.\n\n")
        f.write("> [!TIP]\n")
        f.write(f"> These mappings can be manually adjusted by editing the config file at `{config_path}`.\n\n")
        
        for name in mappings_metadata:
            f.write(f"## {name}\n\n")
            f.write("| Milestone | Col Index | Row 0 (ID/Code) | Row 1 (WBS Stage) | Row 2 (Task Name) | Row 3 (Display Header) |\n")
            f.write("| :--- | :---: | :--- | :--- | :--- | :--- |\n")
            for ms in milestones:
                meta = mappings_metadata[name][ms]
                f.write(f"| **{ms}** | {meta['col_idx']} | `{meta['header_0']}` | {meta['header_1']} | {meta['header_2']} | `{meta['header_3']}` |\n")
            f.write("\n---\n\n")
            
    # Generate Output 2: output/Milestone_Progress_Report_2026.md
    with open(output_report, 'w', encoding='utf-8') as f:
        f.write(f"# Milestone Progress Report - Year {target_year}\n\n")
        f.write(f"This progress report shows month-by-month completions for the target year **{target_year}**.\n\n")
        
        f.write("## 1. Combined Monthly Progress (All Projects)\n\n")
        f.write("| Milestone | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | **Total** |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        for ms in milestones:
            m_counts = [combined_stats[ms][m] for m in range(1, 13)]
            total = sum(m_counts)
            f.write(f"| **{ms}** | " + " | ".join(map(str, m_counts)) + f" | **{total}** |\n")
            
        f.write("\n## 2. Progress Breakdown by Project & DU Model\n\n")
        projects_grouped = {
            "Malaysia CelcomDigi Project": ["2023 TX Rollout", "2024 Celcomdigi BAU", "Jendela TX Migration", "TX Mini Project"],
            "CelcomDigi MW": ["MW EOS Swap", "ZTE TX MINI"]
        }
        for proj, models in projects_grouped.items():
            f.write(f"### Project: {proj}\n\n")
            for model_name in models:
                if model_name in file_stats:
                    f.write(f"#### DU Model: {model_name}\n\n")
                    f.write("| Milestone | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | **Total** |\n")
                    f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
                    for ms in milestones:
                        m_counts = [file_stats[model_name][ms][m] for m in range(1, 13)]
                        total = sum(m_counts)
                        f.write(f"| **{ms}** | " + " | ".join(map(str, m_counts)) + f" | **{total}** |\n")
                    f.write("\n")

        f.write("\n## 3. SLA & KPI Performance\n\n")
        f.write("This section tracks the cycle-time durations and SLA compliance for active, open-ended backlogs (sites where the starting milestone has occurred but the target milestone is not yet completed, calculated from start date until today):\n")
        f.write("* **MC ➔ MOS**: Material Collection to Material On Site (Target: < 14 days, Warning: 10-13 days)\n")
        f.write("* **TI ➔ L1**: Telecom Installation to Q&EHS L1 Approved (Target: < 14 days, Warning: 10-13 days)\n")
        f.write("* **MC ➔ PAC**: Material Collection to Preliminary Acceptance Certification (Target: < 30 days, Warning: 25-29 days)\n\n")
        f.write("> [!NOTE]\n")
        f.write("> Compliance % is calculated as `(Within SLA + Warning) / Open Backlog * 100` representing completed tasks within their respective SLA limits (14 days for MC->MOS & TI->L1, 30 days for MC->PAC).\n\n")
        
        f.write("### Combined SLA Performance (All Projects)\n\n")
        f.write("| KPI Milestone | Open Backlog | Within SLA | Warning | Critical (Breached) | Compliance % | Avg Days Open |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
        f.write(format_sla_row("MC ➔ MOS", combined_sla_stats["MC_MOS"]) + "\n")
        f.write(format_sla_row("TI ➔ L1", combined_sla_stats["TI_L1"]) + "\n")
        f.write(format_sla_row("MC ➔ PAC", combined_sla_stats["MC_PAC"]) + "\n\n")
        
        f.write("### SLA Performance Breakdown by Project & DU Model\n\n")
        for proj, models in projects_grouped.items():
            f.write(f"#### Project: {proj}\n\n")
            for model_name in models:
                if model_name in file_sla_stats:
                    f.write(f"##### DU Model: {model_name}\n\n")
                    f.write("| KPI Milestone | Open Backlog | Within SLA | Warning | Critical (Breached) | Compliance % | Avg Days Open |\n")
                    f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
                    f.write(format_sla_row("MC ➔ MOS", file_sla_stats[model_name]["MC_MOS"]) + "\n")
                    f.write(format_sla_row("TI ➔ L1", file_sla_stats[model_name]["TI_L1"]) + "\n")
                    f.write(format_sla_row("MC ➔ PAC", file_sla_stats[model_name]["MC_PAC"]) + "\n\n")

    print("\n========================================================")
    print("ANALYSIS COMPLETE!")
    print(f"  - Column mapping mappings saved to: {output_mappings}")
    print(f"  - Progress report document saved to: {output_report}")
    print("========================================================")

if __name__ == "__main__":
    main()
