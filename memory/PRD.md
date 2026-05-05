# PRD – Drilling Campaign Cost Estimator (Data Upload Workflow)

## Original Problem Statement
Move data used by the app from loading inside repo path to upload compatibility. User experience: landing page for uploading raw data → upload raw data (including sheet selection) → WBS tree validation → auto-create modelling artifacts → modelling page → audit output.

## Architecture
- **Framework**: Python / Streamlit 1.46.1
- **UI Pattern**: Multipage navigation (st.navigation + st.Page)
- **Storage**: Local filesystem (`data/uploads/` staging, `data/raw/` active)
- **Processing**: ETL pipeline (src/io, src/cleaning, src/modeling)
- **Branch**: `feat/data-upload-workflow` (off `main`)

## User Personas
- Drilling cost engineer uploading Excel/CSV data files for cost estimation
- Team lead validating WBS trees before estimation runs

## Core Requirements
1. Upload page as landing page (xlsx, xls, csv)
2. Sheet selection dropdown for multi-sheet Excel files
3. File content validation (data contract checking)
4. WBS tree validation page
5. Automatic modelling artifact creation (ETL pipeline)
6. Modelling page (cost estimation calculator)
7. Audit output page

## What's Been Implemented (Jan 2026)

### Session 1 - Multipage Upload Workflow
- [x] New branch `feat/data-upload-workflow` created
- [x] Multipage Streamlit app with 5 pages (Upload, Build Artifacts, WBS Tree, Modelling, Audit)
- [x] Upload page with file upload, sheet selection dropdown, file preview
- [x] Encrypted file detection (DRM/OLE) with graceful error handling

### Session 2 - Validation & E2E
- [x] **File content validation**: Data contract validation against expected sheet headers
  - Dashboard workbook contract: Structured.Cost, General.Camp.Data, DashBoard.Tab.Template, Check.Total
  - Primary workbook contract: Data.Summary, WellView.Data
  - Automatic file type detection (dashboard vs primary vs unknown)
  - Pass/fail indicators per sheet with missing header reporting
- [x] **Build Artifacts resilience**: Pipeline handles DRM-encrypted files gracefully (skips with warnings, doesn't crash)
- [x] **E2E verified**: Upload → Validation → Build Artifacts → Modelling → Result (27.90 MMUSD for 3 wells)
- [x] 18 backend unit tests + full UI test suite (100% pass rate)

## Data Contract Reference
| Workbook Type | Required Sheets | Key Headers |
|---|---|---|
| Dashboard | Structured.Cost | Asset, Campaign, Level 2-5, Well, Actual Cost USD |
| Dashboard | General.Camp.Data | Asset, Campaign, WBS CODE, Well Name Actual/SAP/Alt |
| Primary | Data.Summary | Campaign, Well Name |

## Prioritized Backlog
### P0 (Critical)
- [ ] Azure AD authentication integration
- [ ] Handle DRM-encrypted files on Linux (decrypt or require unencrypted uploads)

### P1 (Important)
- [ ] Session-based upload tracking (tie uploads to user sessions once auth is added)
- [ ] Upload history / version management
- [ ] Data quality scoring after validation (completeness, missing values)

### P2 (Nice to have)
- [ ] Batch sheet selection (select multiple sheets from one file)
- [ ] Upload progress indicator for large files
- [ ] Validation report export (PDF/CSV)

## Next Tasks
1. Azure AD integration (user mentioned as future plan)
2. Data quality scoring/dashboard after upload
3. Partial pipeline execution (skip steps where prerequisites are missing)
