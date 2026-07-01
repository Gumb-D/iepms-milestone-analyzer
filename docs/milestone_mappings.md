# Project Milestone vs Column Header Mappings

This document defines the column header mappings used to extract milestone completion dates across all projects.

> [!TIP]
> These mappings can be manually adjusted by editing the config file at `D:\dev\projects\iepms-milestone-analyzer\scripts\milestone_config.json`.

## 2023 TX Rollout

| Milestone | Col Index | Row 0 (ID/Code) | Row 1 (WBS Stage) | Row 2 (Task Name) | Row 3 (Display Header) |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **SOW** | 82 | `WPC000013914|AC0000157842|actual_end_date` | TX Planning | TX Planning | `actual end time` |
| **TSS** | 132 | `WP10400|AC0000079293|actual_end_date` | Survey&Design | Physical Survey | `actual end time` |
| **MC** | 205 | `WP11000|AC0000079297|actual_end_date` | Ready For Installation | Material Collection | `actual end time` |
| **MOS** | 211 | `WP10500|AC0000079298|actual_end_date` | Material On Site | Material On Site | `actual end time` |
| **TI** | 217 | `WP11100|AC0000079299|actual_end_date` | Telecom Installation | Equipment Installation | `actual end time` |
| **L1** | 325 | `WPC000011222|AC0000079322|actual_end_date` | Q&EHS | L1 Approved | `actual end time` |
| **RFS** | 230 | `WP11400|AC0000079301|actual_end_date` | Software Commissioning | TX Integrated | `actual end time` |
| **PAC** | 310 | `WP12000|AC0000079309|actual_end_date` | (Preliminary/Provisional) Acceptance Certification | PAC Approved | `actual end time` |

---

## 2024 Celcomdigi BAU

| Milestone | Col Index | Row 0 (ID/Code) | Row 1 (WBS Stage) | Row 2 (Task Name) | Row 3 (Display Header) |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **SOW** | 182 | `WPC000013914|AC0000162619|actual_end_date` | TX Planning | TX Planning | `actual end time` |
| **TSS** | 47 | `WP10400|AC0000123015|actual_end_date` | Survey&Design | TSSR Customer Approval | `actual end time` |
| **MC** | 51 | `WP11000|AC0000122983|actual_end_date` | Ready For Installation | Material Collection | `actual end time` |
| **MOS** | N/A | `N/A` | N/A | N/A | `N/A` |
| **TI** | 250 | `WP11100|AC0000122984|actual_end_date` | Telecom Installation | Equipment Installation | `actual end time` |
| **L1** | 53 | `WPC000011222|AC0000123006|actual_end_date` | Q&EHS | L1 Approved | `actual end time` |
| **RFS** | 163 | `docata|ZDCSZ00996420` | Installation | Wireless RAN | `Tx Integration End Date` |
| **PAC** | 73 | `WP12000|AC0000123003|actual_end_date` | (Preliminary/Provisional) Acceptance Certification | PAC Approved | `actual end time` |

---

## Jendela TX Migration

| Milestone | Col Index | Row 0 (ID/Code) | Row 1 (WBS Stage) | Row 2 (Task Name) | Row 3 (Display Header) |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **SOW** | 538 | `` |  |  | `` |
| **TSS** | 14 | `docata|ZDCSZ641765` | Installation | Wireless RAN | `Subcon PR - TI` |
| **MC** | 64 | `` |  |  | `` |
| **MOS** | 78 | `` |  |  | `` |
| **TI** | 92 | `` |  |  | `` |
| **L1** | 311 | `` |  |  | `` |
| **RFS** | 143 | `` |  |  | `` |
| **PAC** | 281 | `` |  |  | `` |

---

## MW EOS Swap

| Milestone | Col Index | Row 0 (ID/Code) | Row 1 (WBS Stage) | Row 2 (Task Name) | Row 3 (Display Header) |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **SOW** | 248 | `WPC000014714|AC0000177206|actual_end_date` | TX Planning | TX Planning | `actual end time` |
| **TSS** | 110 | `WP10400|AC0000145865|actual_end_date` | Rollout | Physical Survey | `actual end time` |
| **MC** | 140 | `WP11000|AC0000145869|actual_end_date` | Warehouse | Material Collection | `actual end time` |
| **MOS** | 145 | `WP10500|AC0000145870|actual_end_date` | Rollout | Material On Site | `actual end time` |
| **TI** | 156 | `WP11100|AC0000145871|actual_end_date` | Rollout | Equipment Installation | `actual end time` |
| **L1** | 162 | `WPC000013474|AC0000145901|actual_end_date` | Q&EHS | L1 Approved | `actual end time` |
| **RFS** | 167 | `WP11400|AC0000145873|actual_end_date` | Operation | Site Integrated | `actual end time` |
| **PAC** | 233 | `WP12000|AC0000145882|actual_end_date` | (Preliminary/Provisional) Acceptance Certification | PAC Approved | `actual end time` |

---

## TX Mini Project

| Milestone | Col Index | Row 0 (ID/Code) | Row 1 (WBS Stage) | Row 2 (Task Name) | Row 3 (Display Header) |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **SOW** | 250 | `WPC000013914|AC0000157841|plan_end_date` | TX Planning | TX Planning | `planned end time` |
| **TSS** | 70 | `WP10400|AC0000111560|plan_end_date` | Survey&Design | Physical Survey | `planned end time` |
| **MC** | 96 | `WP11000|AC0000111565|plan_end_date` | Ready For Installation | Material Collection | `planned end time` |
| **MOS** | 101 | `WP10500|AC0000111566|plan_end_date` | Material On Site | Material On Site | `planned end time` |
| **TI** | 107 | `WP11100|AC0000111567|plan_end_date` | Telecom Installation | Equipment Installation | `planned end time` |
| **L1** | 128 | `WPC000011222|AC0000111592|plan_end_date` | Q&EHS | L1 Approved | `planned end time` |
| **RFS** | 119 | `WP11400|AC0000111569|plan_end_date` | Software Commissioning | TX Integrated | `planned end time` |
| **PAC** | 222 | `WP12000|AC0000111579|plan_end_date` | (Preliminary/Provisional) Acceptance Certification | PAC Approved | `planned end time` |

---

## ZTE TX MINI

| Milestone | Col Index | Row 0 (ID/Code) | Row 1 (WBS Stage) | Row 2 (Task Name) | Row 3 (Display Header) |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **SOW** | 10 | `WPC000014714|AC0000197770|plan_end_date` | TX Planning | TX Planning | `planned end time` |
| **TSS** | 43 | `docata|ZDCSZ01096515` | Site Acquisition \AC Power Access | Microwave | `NE Structure Type` |
| **MC** | 109 | `docata|ZDCSZ01027726` | Network Planning | Microwave | `DO Remarks` |
| **MOS** | 112 | `WP11000|AC0000197590|responsible_user` | Ready For Installation | Material Collection | `responsible person` |
| **TI** | 115 | `WP10500|AC0000197592|responsible_user` | Material On Site | Material On Site | `responsible person` |
| **L1** | 127 | `docata|ZDCSZ01027728` | Installation | Microwave | `HO remarks` |
| **RFS** | 118 | `WP11100|AC0000197591|responsible_user` | Telecom Installation | Equipment Installation | `responsible person` |
| **PAC** | 148 | `WPC000013475|AC0000197768|responsible_user` | CD ATP Approval | CD ATP Approval | `responsible person` |

---

