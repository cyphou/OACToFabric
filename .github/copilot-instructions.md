<!-- Copilot instructions for the Oracle Analytics Cloud to Microsoft Fabric migration project -->

# Project: Oracle Analytics Cloud to Microsoft Fabric Migration

Automated migration of Oracle Analytics Cloud artifacts to Microsoft Fabric format.

## Architecture — Pipeline

```
Oracle Analytics Cloud source → [src/agents, src/api, src/cli, src/clients, src/connectors, src/core, src/plugins, src/testing, src/tools, src/validation, src/__pycache__] → Extraction → [output, src/deployers] → Microsoft Fabric
```

## Project Structure

- **Source / Extraction**: `src/agents/`, `src/api/`, `src/cli/`, `src/clients/`, `src/connectors/`, `src/core/`, `src/plugins/`, `src/testing/`, `src/tools/`, `src/validation/`, `src/__pycache__/`
- **Target / Generation**: `output/`, `src/deployers/`
- **Tests**: `tests/` (163 test files)
- **Docs**: `docs/`

## Key Modules

- **Extraction**:
  - `src\agents\discovery\rpd_parser.py`
  - `src\agents\etl\dataflow_parser.py`
  - `src\agents\report\bip_parser.py`
  - `src\agents\semantic\rpd_model_parser.py`
  - `src\core\appinsights_exporter.py`
  - `src\core\onboarding\env_scanner.py`
  - `src\core\rpd_binary_parser.py`
  - `src\core\streaming_parser.py`
- **Generation**:
  - `scripts\_fix_pbir.py`
  - `scripts\_pbir_diag.py`
  - `scripts\audit_tmdl.py`
  - `scripts\generate_architecture_slide.py`
  - `scripts\generate_business_deck.py`
  - `scripts\generate_equivalence_slide.py`
  - `scripts\generate_m365_slide.py`
  - `scripts\generate_oneslider.py`
  - `scripts\generate_services_slide.py`
  - `scripts\html_report_generator.py`
  - `scripts\verify_tmdl.py`
  - `src\agents\etl\fabric_pipeline_generator.py`
  - `src\agents\etl\writeback_generator.py`
  - `src\agents\report\bookmark_generator.py`
  - `src\agents\report\goals_generator.py`
  - ... and 21 more
- **Conversion**:
  - `src\agents\etl\schedule_converter.py`
  - `src\agents\report\prompt_converter.py`
  - `src\agents\report\theme_converter.py`
  - `src\agents\security\rls_converter.py`
  - `src\agents\semantic\dax_optimizer.py`
  - `src\tools\dax_validator.py`
- **Assessment**:
  - `examples\validate_samples.py`
  - `src\agents\discovery\ai_assessor.py`
  - `src\agents\discovery\assessment_narrator.py`
  - `src\agents\discovery\complexity_scorer.py`
  - `src\agents\discovery\portfolio_assessor.py`
  - `src\agents\discovery\strategy_recommender.py`
  - `src\agents\validation\__init__.py`
  - `src\agents\validation\data_reconciliation.py`
  - `src\agents\validation\report_validator.py`
  - `src\agents\validation\schema_drift.py`
  - `src\agents\validation\security_validator.py`
  - `src\agents\validation\semantic_validator.py`
  - `src\agents\validation\validation_agent.py`
  - `src\core\doc_validator.py`
  - `src\core\syntax_validator.py`
  - ... and 2 more
- **Deployment**:
  - `scripts\deploy.py`
  - `src\agents\discovery\oac_client.py`
  - `src\api\auth.py`
  - `src\clients\__init__.py`
  - `src\clients\fabric_client.py`
  - `src\clients\oac_auth.py`
  - `src\clients\oac_catalog.py`
  - `src\clients\oac_dataflow_api.py`
  - `src\clients\pbi_client.py`
  - `src\core\lakehouse_client.py`
  - `src\core\llm_client.py`
  - `src\core\telemetry.py`
  - `src\deployers\__init__.py`
  - `src\deployers\blue_green.py`
  - `src\deployers\container_deploy.py`
  - ... and 7 more
- **Orchestration**:
  - `src\agents\orchestrator\__init__.py`
  - `src\agents\orchestrator\dag_engine.py`
  - `src\agents\orchestrator\monitoring.py`
  - `src\agents\orchestrator\notification_manager.py`
  - `src\agents\orchestrator\orchestrator_agent.py`
  - `src\agents\orchestrator\recovery_report.py`
  - `src\agents\orchestrator\sla_tracker.py`
  - `src\agents\orchestrator\wave_planner.py`
  - `src\cli\__init__.py`
  - `src\cli\config_loader.py`
  - `src\cli\main.py`
  - `src\cli\onboard.py`
  - `src\core\intelligence\orchestration.py`
  - `src\tools\reconciliation_cli.py`
- **Utilities**:
  - `examples\essbase_migration_example.py`
  - `examples\full_migration_example.py`
  - `examples\plugins\custom_connector_example.py`
  - `scripts\_check_cal.py`
  - `scripts\_check_empty.py`
  - `scripts\_check_pages.py`
  - `scripts\_check_pbi_report.py`
  - `scripts\_diag_expr.py`
  - `scripts\_diag_visuals.py`
  - `scripts\_m_diag.py`
  - `scripts\_name_conflicts.py`
  - `scripts\diagnose_m.py`
  - `scripts\essbase_html_report.py`
  - `scripts\run_pilot.py`
  - `scripts\verify_all.py`
  - ... and 110 more

## Hard Constraints

1. **Read before write** — never assume file contents from memory
2. **Test after every change** — run `pytest tests/ --tb=short -q`
3. **No duplicate functions** — always search for an existing name before creating one
4. **Git hygiene** — commit only when tests pass, conventional messages (`feat:`, `fix:`, `test:`, `docs:`)

## Multi-Agent Architecture

This project uses a specialized agent architecture. See `docs/AGENTS.md` for the full
architecture diagram and `.github/agents/` for per-agent definitions.

## Workflow Rules

### 1. Plan Before Build
- For multi-step work, create a plan before starting
- If something goes sideways, STOP and re-plan

### 2. Read Before Write
- **Always read target code before editing**
- Read `copilot-instructions.md` at session start for project rules

### 3. Testing Contract
- Run `pytest tests/ --tb=short -q` after EVERY implementation change
- If tests fail → fix them before reporting completion
- New features **require** new tests
- Never weaken test assertions to make tests pass

### 4. Scope Discipline
- Only modify files directly related to the task
- No drive-by refactors
- Prefer the smallest change that solves the problem
