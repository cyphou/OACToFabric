# Security Considerations

## Overview

This document describes how the OAC → Fabric & Power BI migration framework handles sensitive data, credentials, and access control.

---

## Credential Management

### Stored Credentials

| Credential | Storage | Access |
|---|---|---|
| OAC IDCS client ID/secret | Environment variables or `.env` file | Read by `oac_auth.py` |
| Fabric service principal | Environment variables or Azure Key Vault | Read by `fabric_client.py` |
| Azure OpenAI API key | Environment variables | Read by `llm_client.py` |
| Power BI XMLA endpoint | Environment variables | Read by `pbi_deployer.py` |

### Best Practices

- **Never commit `.env` files** — `.gitignore` excludes them.
- **Use Azure Key Vault** in production — reference secrets via `@Microsoft.KeyVault(...)`.
- **Rotate credentials** after each migration run.
- **Service principals** should have minimum required permissions:
  - Fabric: Contributor role on the target workspace only.
  - Power BI: Dataset.ReadWrite.All, Report.ReadWrite.All.
  - OAC: Read-only catalog access.

---

## Data Handling

### Data in Transit

- All API calls use HTTPS/TLS 1.2+.
- OAC REST API: OAuth2 bearer tokens over HTTPS.
- Fabric REST API: Azure AD tokens over HTTPS.
- Azure OpenAI: API key over HTTPS.

### Data at Rest

- **Checkpoint files** (`.checkpoint.json`): Contain run metadata (IDs, wave numbers), no sensitive data.
- **Migration output**: Generated TMDL, DDL scripts, and validation reports are stored in the local `output/` directory.
- **Translation cache**: Cached LLM responses stored locally. Contains expression text but no PII unless expressions reference sensitive column names.
- **Lakehouse coordination tables**: Stored in Fabric with workspace-level security.

### Data Not Collected

The framework does **NOT**:
- Copy actual data values (row-level data) outside of reconciliation checks.
- Store credentials in logs, output files, or coordination tables.
- Send PII to Azure OpenAI (only expression syntax is sent for translation).

---

## Access Control

### OAC (Source)

- Read-only access — the framework never modifies OAC.
- IDCS application role with `BI Consumer` or `BI Author` permissions.

### Fabric (Target)

- Service principal with workspace Contributor role.
- RLS roles are created but not assigned to users (assignment is a post-migration step).

### Power BI (Target)

- XMLA read/write endpoint must be enabled on the workspace.
- Service principal must be in a security group allowed for XMLA access.

---

## Audit Trail

All agent actions are logged to:
1. **Python structured logging** (console + file).
2. **Notification log** (`notification_log.md`).
3. **Lakehouse `agent_logs` table** (when connected).
4. **Azure Application Insights** (when configured).

Each log entry includes:
- `run_id` — Unique migration run identifier.
- `agent_id` — Which agent performed the action.
- `timestamp` — UTC timestamp.
- `action` — What was done.

---

## LLM Security

When Azure OpenAI is used for expression translation:
- Only expression **syntax** is sent (e.g., `SUM(Sales.Amount)`).
- No table data, PII, or credentials are included in prompts.
- Azure OpenAI data is **not** used for model training (per Azure data processing terms).
- Token budgets prevent runaway costs from compromised or malformed inputs.

---

## Network Security

### Required Outbound Endpoints

| Endpoint | Port | Purpose |
|---|---|---|
| OAC instance (e.g., `*.oraclecloud.com`) | 443 | Discovery, catalog APIs |
| `login.microsoftonline.com` | 443 | Azure AD authentication |
| `*.fabric.microsoft.com` | 443 | Fabric REST API |
| `*.analysis.windows.net` | 443 | Power BI XMLA endpoint |
| `*.openai.azure.com` | 443 | Azure OpenAI (if LLM enabled) |

### Firewall Recommendations

- Allow outbound HTTPS (443) to the endpoints above.
- Block all other outbound traffic from the migration host.
- Run the migration from a secured Azure VM or container, not a developer workstation.

---

## Incident Response

If a security issue is discovered during migration:

1. **Stop the migration** immediately (Ctrl+C or `SIGTERM`).
2. **Rotate all credentials** (OAC, Fabric, OpenAI).
3. **Audit logs** in Application Insights for unauthorized access.
4. **Delete sensitive output** from the `output/` directory.
5. **Report** to the security team with run details.
