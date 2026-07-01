# IEPMS Milestone Progress Analyzer

This workspace is organized into dedicated subdirectories to isolate data inputs, code execution scripts, and generated outputs.

## 📁 Directory Layout

* **`input/`**: Contains the source project data files (both `.xlsx` Excel workbooks and `.csv` files).
* **`scripts/`**: Contains the executable scripts and configuration files:
  * `IEPMS_Milestone_Analyzer.py`: The main analyzer tool.
  * `milestone_config.json`: Decoupled column mapping configuration.
  * `Convert-XlsxToCsv.ps1` / `.lnk`: PowerShell converter backups.
* **`output/`**: Contains the generated monthly progress reports (e.g. `Milestone_Progress_Report_2026.md`).
* **`docs/`**: Contains `milestone_mappings.md` (documenting column headers).
* **`iepms_skill/`**: The OpenClaw instruction-based skill plugin (contains `SKILL.md`).
* **`README.md`**: This main user guide (located in the project root).

---

## 📖 Operation Guide (Step-by-Step Workflow)

Follow these steps for routine data updates and report generation:

### Step 1: Place New Project Files in `input/`
When you receive updated Excel workbooks (`.xlsx`) or CSV sheets (`.csv`) for your projects:
1. Open the **`input/`** folder.
2. Copy the new files into this folder, overwriting the old files (keep the original filenames identical so the script knows which project configuration to apply).
   * *Note: You can copy either `.xlsx` or `.csv` files. The tool handles both formats.*

### Step 2: Run the Analyzer Script
Open your terminal (PowerShell, Command Prompt, or Git Bash) in the project root folder (`C:\temp\iepms`) and execute the following command:
```bash
python scripts/IEPMS_Milestone_Analyzer.py
```
This runs the default H1/Full-Year analysis for the year **2026**.

* **What happens behind the scenes:**
  1. The script checks the **`input/`** folder for any `.xlsx` files.
  2. If a `.csv` version is missing or is older than the `.xlsx` file, the script automatically converts it to `.csv` with exact UTF-8 BOM encoding.
  3. The script loads mappings from **`scripts/milestone_config.json`**.
  4. It processes the CSV files and aggregates completion counts month-by-month.

### Step 3: Retrieve and Review Reports
Once the command completes, you will find your outputs ready:
* **Progress Report**: Open **`output/Milestone_Progress_Report_2026.md`** to view the combined progress table and individual project breakdown tables.
* **Column Mappings**: Open **`docs/milestone_mappings.md`** to verify which exact columns were analyzed.

---

## 🚀 How to Run the Tool (Reference Commands)

Run the script from the project root directory:

```bash
python scripts/IEPMS_Milestone_Analyzer.py
```

### 🔧 Custom Controls & Arguments

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
  If the CSV file layouts have changed or new files have been added, force the tool to re-scan the headers (this will overwrite `scripts/milestone_config.json`):
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
