# PRD – Drilling Campaign Cost Estimator (Data Upload Workflow)

## Original Problem Statement
Move data used by the app from loading inside repo path to upload compatibility. User experience: landing page for uploading raw data → upload raw data (including sheet selection) → WBS tree validation → auto-create modelling artifacts → modelling page → audit output.

## Architecture
- **Framework**: Python / Streamlit 1.46.1
- **UI Pattern**: Multipage navigation (st.navigation + st.Page)
- **Storage**: Local filesystem (`data/uploads/` staging, `data/raw/` active)
- **Processing**: ETL pipeline (src/io, src/cleaning, src/modeling)
- **Existing branch**: `feat/data-upload-workflow` (off `main`)

## User Personas
- Drilling cost engineer uploading Excel/CSV data files for cost estimation
- Team lead validating WBS trees before estimation runs

## Core Requirements
1. Upload page as landing page (xlsx, xls, csv)
2. Sheet selection dropdown for multi-sheet Excel files
3. WBS tree validation page
4. Automatic modelling artifact creation (ETL pipeline)
5. Modelling page (cost estimation calculator)
6. Audit output page

## What's Been Implemented (Jan 2026)
- [x] New branch `feat/data-upload-workflow` created
- [x] Multipage Streamlit app with 5 pages (Upload, Build Artifacts, WBS Tree, Modelling, Audit)
- [x] Upload page with file upload, sheet selection dropdown, file preview
- [x] Encrypted file detection (DRM/OLE) with graceful error handling
- [x] Build Artifacts page with step-by-step ETL pipeline execution with progress bar
- [x] Modelling page (preserved from existing stable feature)
- [x] Audit page (shows detail WBS estimator output)
- [x] WBS Tree page (preserved existing viewer)
- [x] All tests passing (100% frontend success rate)

## Prioritized Backlog
### P0 (Critical)
- [ ] Azure AD authentication integration
- [ ] Handle DRM-encrypted files on Linux (currently requires unencrypted uploads)

### P1 (Important)
- [ ] Session-based upload tracking (tie uploads to user sessions once auth is added)
- [ ] File validation on upload (check expected column headers before loading)
- [ ] Upload history / version management

### P2 (Nice to have)
- [ ] Drag-and-drop upload zone styling
- [ ] Batch sheet selection (select multiple sheets from one file)
- [ ] Upload progress indicator for large files
- [ ] Data quality report after upload

## Next Tasks
1. Azure AD integration (user mentioned as future plan)
2. File content validation (verify uploaded data has expected structure)
3. End-to-end test with fresh upload → artifact build → estimation
