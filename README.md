# IEPMS Milestone Progress Analyzer

This workspace is organized into dedicated subdirectories to isolate data inputs, code execution scripts, and generated outputs.

## 📁 Directory Layout

* **`input/`**: Contains the source project data files (both `.xlsx` Excel workbooks and `.csv` files).
* **`scripts/`**: Contains the executable scripts and configuration files:
  * `IEPMS_Milestone_Analyzer.py`: The main analyzer tool.
  * `milestone_config.json`: Decoupled column mapping configuration.
  * `api_auth.json`: Active API authentication headers/cookies (never pushed to git).
  * `Convert-XlsxToCsv.ps1` / `.lnk`: PowerShell converter backups.
* **`output/`**: Contains the generated monthly progress reports (e.g. `Milestone_Progress_Report_2026.md`).
* **`docs/`**: Contains `milestone_mappings.md` (documenting column headers).
* **`iepms_skill/`**: The OpenClaw instruction-based skill plugin (contains `SKILL.md`).
* **`README.md`**: This main user guide (located in the project root).

---

## 📖 Operation Guide (Step-by-Step Workflow)

There are two ways to operate the tool: **Manual Mode** (where you copy files yourself) and **Automated Fetch Mode** (where the script pulls data directly from the ZTE EPMS API).

### Option A: Manual Mode (Copy & Run)
1. **Place new files**: Download the Excel sheets manually, rename them to clean, normalized names (e.g., `2023_TX_Rollout.xlsx`), and place them in the **`input/`** folder.
2. **Run analysis**: Open your terminal in the project root and run:
   ```bash
   python scripts/IEPMS_Milestone_Analyzer.py --year 2026
   ```

---

### Option B: Automated Fetch Mode (Direct API download) 🚀
Instead of manually exporting, renaming, and copying the files, the script can query and download the completed sheets directly from the ZTE EPMS servers:

1. **Submit the Export**: Log into the ZTE IEPMS portal and click **Export** on the project sheets you want to update (this schedules the export tasks on the server).
2. **Grab Authentication Headers**:
   * Open Developer Tools (**F12**), select the **Network** tab, and click "Download" on any completed export sheet in the "View Export Result" modal.
   * Right-click the download network request, select **Copy as cURL**, and locate the `Cookie` string and the `X-Auth-Value` header.
3. **Save Credentials**:
   * Create or open **`scripts/api_auth.json`** (if it doesn't exist, run `python scripts/IEPMS_Milestone_Analyzer.py --fetch` once to generate a template).
   * Paste your active **`cookie`** string and **`x_auth_value`** into the JSON file.
   * *(Optional)* If you want to download ZTE Project files (`MW_EOS_Swap` and `ZTE_TX_MINI`), switch to that project in the browser, copy its `projId` from the request headers, and paste it under the `ZTE_Mini_Project` section in `scripts/api_auth.json`.
4. **Run Automated Fetch & Analyze**:
   Run the script with the `--fetch` flag:
   ```bash
   python scripts/IEPMS_Milestone_Analyzer.py --fetch --year 2026
   ```
   *The script will query your export records list, identify the latest completed file for each project, download them to `input/`, convert them, and compile the progress report in one step!*

---

## 🚀 How to Run the Tool (Reference Commands)

Run the script from the project root directory:

```bash
python scripts/IEPMS_Milestone_Analyzer.py
```

### 🔧 Custom Controls & Arguments

* **Fetch and Analyze**:
  ```bash
  python scripts/IEPMS_Milestone_Analyzer.py --fetch --year 2026
  ```
* **Run for a Different Year (e.g., 2025)**:
  ```bash
  python scripts/IEPMS_Milestone_Analyzer.py --year 2025
  ```
* **Force Re-convert Excel Files**:
  ```bash
  python scripts/IEPMS_Milestone_Analyzer.py --force-convert
  ```
* **Disable Excel Conversion Checking**:
  ```bash
  python scripts/IEPMS_Milestone_Analyzer.py --no-convert
  ```
* **Force Auto-detect Column Headers**:
  If the sheet layouts change and you want the script to re-detect columns:
  ```bash
  python scripts/IEPMS_Milestone_Analyzer.py --force-detect
  ```

---

## 📊 Milestone Mapping Logic

The analyzer maps the project milestones to the following columns:
1. **SOW**: Scope of Work (`TX Planning` actual end time).
2. **TSS**: Technical Site Survey (`Physical Survey` / `TSSR Customer Approval` actual end time).
3. **MC**: Material Collection (`Material Collection` actual end time).
4. **MOS**: Material On Site (`Material On Site` actual end time).
5. **TI**: Telecom Installation (`Equipment Installation` actual end time).
6. **L1**: Q&EHS L1 Approved (`L1 Approved` actual end time).
7. **RFS**: Ready for Service (`Site Integrated` / `TX Integrated` actual end time).
8. **PAC**: Preliminary Acceptance Certification (`PAC Approved` actual end time).

---

## ⚙️ Decoupling Configuration from Code

The column mappings are stored in `scripts/milestone_config.json`. If any mapping needs manual refinement:
1. Open `scripts/milestone_config.json`.
2. Locate the specific filename and milestone key.
3. Update the integer index of the column (0-based, representing the Excel sheet column).
4. Re-run `python scripts/IEPMS_Milestone_Analyzer.py` (do **not** pass `--force-detect` or your manual changes will be overwritten).
