import os
import csv
import re
import json
import argparse
import datetime
import warnings

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
        
        # Apply clean formatting element-wise
        if hasattr(df, 'map'):
            df = df.map(format_excel_cell)
        else:
            df = df.applymap(format_excel_cell)
            
        # Write with UTF-8 BOM encoding ('utf-8-sig') to match existing layout
        df.to_csv(csv_path, index=False, header=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        print(f"Failed to convert {os.path.basename(xlsx_path)}: {e}")
        return False

def check_and_convert_all_xlsx(input_dir, force_convert=False):
    """
    Scans the input directory for .xlsx files and converts them to .csv files
    if they are newer than existing CSVs or if CSVs are missing.
    """
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
    """
    Scans CSV files in input_dir and automatically maps milestones to column indices.
    """
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

def fetch_files_from_api(script_dir, input_dir):
    """
    Downloads Excel files directly from ZTE EPMS API using headers, cookies and config
    defined in scripts/api_auth.json.
    """
    if requests is None:
        print("Error: 'requests' library is required to fetch files from API.")
        return False
        
    auth_path = os.path.join(script_dir, "api_auth.json")
    if not os.path.exists(auth_path):
        # Create a template configuration file
        template = {
            "cookie": "RedirectedToNewiCenter=1; ZTEDPGSSOCookie=YOUR_SSO_TOKEN; ZTEDPGSSOUser=YOUR_EMP_NO; ...",
            "x_auth_value": "YOUR_AUTH_VALUE_FROM_F12_HEADERS",
            "x_emp_no": "YOUR_EMP_NO",
            "projects": {
                "CD_BAU_Project": {
                    "projId": "c46633e8-6e52-2178-f17e-dcbfdade7cb2",
                    "files": {
                        "2023 TX Rollout": "2023_TX_Rollout",
                        "2024 Celcomdigi BAU": "2024_Celcomdigi_BAU",
                        "Jendela TX Migration": "Jendela_TX_Migration",
                        "TX Mini Project": "TX_Mini_Project"
                    }
                },
                "ZTE_Mini_Project": {
                    "projId": "PASTE_YOUR_ZTE_PROJECT_PROJID_HERE",
                    "files": {
                        "MW EOS Swap": "MW_EOS_Swap",
                        "ZTE TX MINI": "ZTE_TX_MINI"
                    }
                }
            }
        }
        with open(auth_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=4)
        print("=========================================================================")
        print("API AUTHENTICATION FILE NOT FOUND!")
        print(f"Created a configuration template at: {auth_path}")
        print("Please follow the README to populate Cookie and X-Auth-Value from F12 console.")
        print("=========================================================================")
        return False

    with open(auth_path, 'r', encoding='utf-8') as f:
        auth = json.load(f)

    # Base headers
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6,ms;q=0.5',
        'Connection': 'keep-alive',
        'Internal': '1',
        'Referer': 'https://iepms.zte.com.cn/zte-crm-iepms-scheduleui/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
        'X-Auth-Value': auth.get("x_auth_value", ""),
        'X-Emp-No': auth.get("x_emp_no", ""),
        'X-Lang-Id': 'en_US',
        'X-Org-Id': '1',
        'X-Origin-ServiceName': 'zte-crm-iepms-schedule',
        'X-Target-ServiceName': 'zte-crm-iepms-schedule',
        'X-Tenant-Id': '10001'
    }

    # Format cookies dictionary from the raw string
    cookie_str = auth.get("cookie", "")
    cookies = {}
    for item in cookie_str.split(";"):
        if "=" in item:
            k, v = item.strip().split("=", 1)
            cookies[k] = v

    print("Fetching export records list from ZTE EPMS API...")
    record_url = "https://iepms.zte.com.cn/zte-crm-iepms-basebff/zte-crm-iepms-schedule/record"
    download_url = "https://iepms.zte.com.cn/zte-crm-iepms-basebff/zte-crm-iepms-schedule/record/download"
    
    success_count = 0
    
    for proj_name, proj_cfg in auth.get("projects", {}).items():
        proj_id = proj_cfg.get("projId")
        if not proj_id or "PASTE" in proj_id:
            print(f"Skipping project {proj_name}: project ID (projId) is not configured.")
            continue
            
        print(f"\nProcessing project: {proj_name} (ID: {proj_id})...")
        
        # Override project ID in request context headers and cookies
        headers['X-Itp-Value'] = f'timeZone=8;projId={proj_id}'
        cookies['projId'] = proj_id
        
        params = {
            'operationType': 'EXPORT',
            'pageNo': '1',
            'pageSize': '20',
            'bizType': 'SCHEDULE'
        }
        
        try:
            response = requests.get(record_url, headers=headers, cookies=cookies, params=params, timeout=30)
            if response.status_code != 200:
                print(f"  Error: Failed to fetch record list (HTTP {response.status_code})")
                continue
                
            data = response.json()
            rows = data.get("bo", {}).get("rows", [])
            
            # Look for matching target files
            for pat, target_name in proj_cfg.get("files", {}).items():
                print(f"  Searching export record matching pattern '{pat}'...")
                matched_row = None
                for row in rows:
                    file_name = row.get("fileName", "")
                    status = row.get("status", "")
                    if pat in file_name and status == "SUCCESS":
                        matched_row = row
                        break
                        
                if not matched_row:
                    print(f"    -> Warning: No completed export record found for '{pat}'!")
                    continue
                    
                file_id = matched_row.get("fileId")
                real_file_name = matched_row.get("fileName")
                print(f"    -> Found completed export: {real_file_name} (ID: {file_id})")
                
                # Download
                dl_params = {'docId': file_id, 'fileName': real_file_name}
                out_path = os.path.join(input_dir, f"{target_name}.xlsx")
                
                print(f"    -> Downloading: {target_name}.xlsx...")
                with requests.get(download_url, headers=headers, cookies=cookies, params=dl_params, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(out_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                print(f"    -> SUCCESS: Saved to {out_path}")
                success_count += 1
                
        except Exception as e:
            print(f"  Error querying or downloading files for project {proj_name}: {e}")
            
    return success_count > 0

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
        success = fetch_files_from_api(script_dir, input_dir)
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
    
    csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv') and f in mappings and "test" not in f]
    
    for f in csv_files:
        path = os.path.join(input_dir, f)
        # Extract friendly name
        friendly_name = f.replace('_', ' ').replace('.csv', '')
        
        file_stats[friendly_name] = {ms: {m: 0 for m in range(1, 13)} for ms in milestones}
        mappings_metadata[friendly_name] = {}
        
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
            
        f.write("\n## 2. Progress Breakdown by Project\n\n")
        for name in file_stats:
            f.write(f"### {name}\n\n")
            f.write("| Milestone | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | **Total** |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n")
            for ms in milestones:
                m_counts = [file_stats[name][ms][m] for m in range(1, 13)]
                total = sum(m_counts)
                f.write(f"| **{ms}** | " + " | ".join(map(str, m_counts)) + f" | **{total}** |\n")
            f.write("\n")

    print("\n========================================================")
    print("ANALYSIS COMPLETE!")
    print(f"  - Column mapping mappings saved to: {output_mappings}")
    print(f"  - Progress report document saved to: {output_report}")
    print("========================================================")

if __name__ == "__main__":
    main()
