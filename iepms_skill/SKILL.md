---
name: analyze_iepms
description: Auto-converts Excel sheets, maps column headers, and generates month-by-month milestone progress reports for IEPMS transmission projects.
tools:
  - execute_command
  - read_file
---

# Instruction Playbook: Analyze IEPMS Milestone Data

Follow these instructions whenever the user asks to analyze IEPMS project files, compile milestone progress, or generate a half-year/yearly report.

## 1. Parameter Extraction
* Ask or look in the conversation context for the target **year** (e.g., `2026`). If not specified, default to `2026`.

## 2. Command Execution
Execute the Python analyzer CLI script using the `execute_command` tool. Run this command from the project root folder `D:/dev/projects/iepms`:

```bash
python D:/dev/projects/iepms/scripts/IEPMS_Milestone_Analyzer.py --year <target_year>
```

*Note: The script automatically handles converting Excel (.xlsx) files inside `D:/dev/projects/iepms/input/` to CSV if they are missing or outdated, and saves configuration mapping in `D:/dev/projects/iepms/scripts/milestone_config.json`.*

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
* Highlight key progress metrics, such as the total Integration (RFS) count year-to-date (YTD) or any major milestone spikes (e.g. PAC in March).
