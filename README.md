# IEPMS Milestone Progress Analyzer

This workspace is organized into dedicated subdirectories to isolate data inputs, code execution scripts, and generated outputs.

> [!IMPORTANT]
> **ZTE NETWORK CONSTRAINT**
> The automated download features in this project communicate directly with `iepms.zte.com.cn`, which is only accessible within the **ZTE Corporate Network** or via **ZTE VPN**. Connection requests will fail or time out if executed outside this network environment.

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

### Option B: Automated Fetch Mode (1-Click Sync Auth) 🚀
Instead of manually exporting, renaming, and copying the files, the script can trigger exports, poll their status, and download them automatically using your active login cookies.

#### 1. Setup Your Browser Bookmarklet (One-Time Setup)
Create a new bookmark in your browser (e.g., Google Chrome or Microsoft Edge) with these properties:
* **Name**: `Sync Auth`
* **URL**: Copy and paste the exact code below into the URL box:
  ```javascript
  javascript:(async()=>{try{const r=await fetch('http://localhost:18290/sync',{method:'POST',body:document.cookie});const d=await r.json();if(d.status==='success')alert('🔒 ZTE EPMS Auth Sync Successful! Check your terminal.');else alert('❌ Sync Failed.');}catch(e){alert('❌ Could not connect. Run the python script first!');}})()
  ```

#### 2. Run the Script
To fetch fresh files and analyze, open your terminal in the project root and run:
```bash
python scripts/IEPMS_Milestone_Analyzer.py --fetch --year 2026
```

#### 3. Instant 1-Click Sync
* If your cookies are **missing or expired**, the script will pause and launch a temporary sync server in the background.
* It will display a message in your terminal asking you to sync.
* **Just open the ZTE IEPMS page in your browser and click your `Sync Auth` bookmark.**
* The browser will pop up a success alert, the sync server will securely save the cookie to `scripts/api_auth.json`, and the terminal script will immediately resume, download the files, and output the report!

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

## ⏱️ SLA & KPI Cycle-Time Monitoring

The script automatically calculates completion durations row-by-row for the following key execution intervals:
1. **MC ➔ MOS** (Material Collection to Material On Site)
2. **TI ➔ L1** (Telecom Installation to Q&EHS L1 Approval)
3. **MC ➔ PAC** (Material Collection to Preliminary Acceptance Certification)

### SLA Compliance Metric Rules
* **Met**: Cycle time was **less than 10 days** (0 to 9 days).
* **Warning**: Cycle time was **between 10 and 13 days** (10 to 13 days).
* **Breached**: Cycle time took **14 days or longer** (≥ 14 days).
* **Pending**: The start milestone has occurred, but the target milestone is still empty.
* **SLA Compliance %**: Calculated as `(Met + Warning) / (Met + Warning + Breached) * 100` (representing total completed tasks completed within the 14-day limit).

---

## ⚙️ Decoupling Configuration from Code

The column mappings are stored in `scripts/milestone_config.json`. If any mapping needs manual refinement:
1. Open `scripts/milestone_config.json`.
2. Locate the specific filename and milestone key.
3. Update the integer index of the column (0-based, representing the Excel sheet column).
4. Re-run `python scripts/IEPMS_Milestone_Analyzer.py` (do **not** pass `--force-detect` or your manual changes will be overwritten).
