#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
pip install pandas openpyxl numpy scipy statsmodels scikit-learn streamlit plotly xlsxwriter
