---
name: analyze_iepms
description: Auto-converts Excel sheets, maps column headers, and generates month-by-month milestone progress reports for IEPMS transmission projects. Can also download files directly from ZTE EPMS API using user cookies.
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
* Check if the user requested to **download**, **fetch**, or **pull** fresh files directly from the server. If so, set the `fetch_flag` to `--fetch`.

## 2. Command Execution
Execute the Python analyzer CLI script using the `execute_command` tool. Run this command from the project root folder `D:/dev/projects/iepms`:

```bash
python D:/dev/projects/iepms/scripts/IEPMS_Milestone_Analyzer.py --year <target_year> <fetch_flag>
```
*(For example, if the user requested to fetch first, run: `python D:/dev/projects/iepms/scripts/IEPMS_Milestone_Analyzer.py --year 2026 --fetch`)*

* **Interactive Auth Sync Handling**:
  If the command outputs `Waiting for sync request...` (indicating the session cookies are missing or expired):
  
  * **Option A: Headless Browser Extraction (Fully Automated)**:
    If your agent runtime is equipped with browser automation capabilities (e.g. Playwright, Puppeteer, `read_browser_page`, `open_browser`):
    1. Navigate to the ZTE IEPMS page: `https://iepms.zte.com.cn`.
    2. Wait for auto-authentication (SSO/VPN) to complete.
    3. Evaluate `document.cookie` on the page to retrieve the cookies.
    4. Write the cookies directly to `D:/dev/projects/iepms/scripts/api_auth.json` under the `"cookie"` key.
    5. Re-run the analyzer command. It will bypass the sync server and succeed immediately.
    
  * **Option B: Bookmarklet Sync (User Interaction)**:
    If browser tools are not available:
    1. STOP execution.
    2. Ask the user in the chat: *"Please open the ZTE IEPMS page in your browser and click your 'Sync Auth' bookmarklet to refresh your session."*
    3. The local server running inside the python script will receive the sync request automatically, write the credentials to `scripts/api_auth.json`, shut down, and resume downloading the files.

## 3. Read and Process Outputs
After the command completes successfully:
1. **Read Column Mappings**: Open and read the mapped column headers documentation from:
   `D:/dev/projects/iepms/docs/milestone_mappings.md`
2. **Read Progress Report**: Open and read the generated monthly progress report from:
   `D:/dev/projects/iepms/output/Milestone_Progress_Report_<target_year>.md`

## 4. Respond to the User
Present the results in a clean, professional response:
* Provide a brief confirmation of the files analyzed and column mappings.
* Display the **Combined Monthly Progress** table for the requested year.
* Highlight key progress metrics, such as the total Integration (RFS) count year-to-date (YTD) or any major milestone spikes.
