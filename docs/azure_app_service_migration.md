# Azure App Service Migration (Streamlit)

This branch is prepared for deployment to an **existing** Azure App Service based on `D:\FAAU\deploy_streamlit_azure.docx`.

## Included in this branch

- Root entrypoint: `app.py`
- Dependency manifest: `requirements.txt`
- Streamlit server config: `.streamlit/config.toml` (port `8000`)
- GitHub Actions pipeline: `.github/workflows/azure-streamlit-deploy.yml`
- Azure runtime setup script: `scripts/azure_configure_app_service.sh`

## Prerequisites to confirm with admin

1. App Service OS is **Linux**.
2. Runtime stack is **Python** (3.11 or 3.12).
3. You have at least **Contributor** or **Website Contributor** access.
4. App Service name and resource group are provided.
5. Plan/SKU is at least **B1** if `Always On` is required.

## One-time Azure runtime configuration

```bash
az login
RG="<resource-group>"
APP_NAME="<app-service-name>"
bash scripts/azure_configure_app_service.sh
```

This configures:

- Startup command:
  - `python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0`
- WebSockets enabled.
- `SCM_DO_BUILD_DURING_DEPLOYMENT=true`.

## GitHub Actions deployment setup

Add these repository secrets:

- `AZURE_WEBAPP_NAME` = Azure App Service name
- `AZURE_WEBAPP_PUBLISH_PROFILE` = publish profile XML from App Service

Then deploy by:

1. Push to `main`, or
2. Trigger `Deploy Streamlit to Azure App Service` via **Actions > Run workflow**.

## Verification

1. Open `https://<APP_NAME>.azurewebsites.net`.
2. Check Azure log stream if needed:

```bash
az webapp log tail --resource-group "$RG" --name "$APP_NAME"
```

## Optional auth hardening

Use Azure App Service Authentication (Easy Auth) with Microsoft Entra ID if login gating is required.
