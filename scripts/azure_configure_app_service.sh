#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   RG="<resource-group>" APP_NAME="<app-service-name>" bash scripts/azure_configure_app_service.sh
#
# Required:
# - Existing Linux App Service with Python runtime (3.11/3.12 recommended)
# - Azure CLI login completed: az login

: "${RG:?RG environment variable is required}"
: "${APP_NAME:?APP_NAME environment variable is required}"

az webapp config set \
  --resource-group "$RG" \
  --name "$APP_NAME" \
  --startup-file "python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0"

az webapp config set \
  --resource-group "$RG" \
  --name "$APP_NAME" \
  --web-sockets-enabled true

az webapp config appsettings set \
  --resource-group "$RG" \
  --name "$APP_NAME" \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=true

# Enable this only for paid tiers (B1+). It fails on Free/F1.
# az webapp config set \
#   --resource-group "$RG" \
#   --name "$APP_NAME" \
#   --always-on true

echo "Azure App Service runtime settings applied for $APP_NAME in $RG."
