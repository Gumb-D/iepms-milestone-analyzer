---
name: iepms-milestone-analyzer
description: Auto-converts Excel sheets, maps column headers, and generates month-by-month milestone progress reports for IEPMS transmission projects. Downloads files directly from ZTE EPMS API using user cookies.
tools:
  - execute_command
  - read_file
---

# Instruction Playbook: Analyze IEPMS Milestone Data

> [!IMPORTANT]
> **ZTE NETWORK CONSTRAINT**
> This skill and its API integration can **only** be executed when connected to the **ZTE Corporate Network** or the **ZTE VPN**. If run outside of the ZTE network, connection attempts to `iepms.zte.com.cn` will time out or fail.

## 1. Parameter Extraction
* Ask or look in the conversation context for the target **year** (e.g., `2026`). If not specified, default to `2026`.
* **Fetch Flag**: **Always default `fetch_flag` to `--fetch`** to guarantee that the agent always downloads the latest data from the ZTE EPMS portal, unless the user explicitly asks to run offline or use local files without fetching.

## 2. Command Execution
Execute the Python analyzer CLI script using the `execute_command` tool. Run this command from the project root folder:

```bash
python scripts/IEPMS_Milestone_Analyzer.py --year <target_year> <fetch_flag>
```
*(For example, since the agent always uses latest data by default, run: `python scripts/IEPMS_Milestone_Analyzer.py --year 2026 --fetch`)*

* **Interactive Auth Sync Handling**:
  If the command outputs `Waiting for sync request...` (indicating the session cookies are missing or expired):
  
  * **Option A: Headless Browser Extraction (Fully Automated)**:
    If your agent runtime is equipped with browser automation capabilities (e.g. Playwright, Puppeteer, `read_browser_page`, `open_browser`):
    1. Navigate to the ZTE IEPMS page: `https://iepms.zte.com.cn`.
    2. Wait for auto-authentication (SSO/VPN) to complete.
    3. Evaluate `document.cookie` on the page to retrieve the cookies.
    4. Write the cookies directly to `scripts/api_auth.json` under the `"cookie"` key.
    5. Re-run the analyzer command. It will bypass the sync server and succeed immediately.
    
  * **Option B: Bookmarklet Sync (User Interaction)**:
    If browser tools are not available:
    1. STOP execution.
    2. Ask the user in the chat: *"Please open the ZTE IEPMS page in your browser and click your 'Sync Auth' bookmarklet to refresh your session."*
    3. The local server running inside the python script will receive the sync request automatically, write the credentials to `scripts/api_auth.json`, shut down, and resume downloading the files.

## 3. Read and Process Outputs
After the command completes successfully:
1. **Read Column Mappings**: Open and read the mapped column headers documentation from:
   `docs/milestone_mappings.md`
2. **Read Progress Report**: Open and read the generated monthly progress report from:
   `output/Milestone_Progress_Report_<target_year>.md`

## 4. Respond to the User
Present the results in a clean, professional response:
* **CRITICAL - Verbatim Tables**: You **MUST copy and print the markdown tables exactly as they are formatted inside the generated report file** (`output/Milestone_Progress_Report_<target_year>.md`). Do **NOT** summarize, compress, or rewrite the tables into custom formats, as this breaks markdown table rendering.
* **Progress Tables (Verbatim)**:
  * Print the **Combined Monthly Progress (All Projects)** table verbatim.
  * Print the **Progress Breakdown by Project** table verbatim for **EACH project** (so the user knows the project-level origin of the progress).
* **SLA Performance Tables (Verbatim)**:
  * Print the **Combined SLA Performance (All Projects)** table verbatim.
  * Print the **SLA Performance Breakdown by Project** table verbatim for **EACH project**.
* Summarize key observations and project-level performance highlights.
