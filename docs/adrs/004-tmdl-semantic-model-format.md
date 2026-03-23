# ADR-004: TMDL as Power BI Semantic Model Format

## Status

**Accepted** — 2025-01

## Context

Power BI semantic models (datasets) can be represented and deployed in several formats:

1. **BIM (JSON)**: Tabular Model Scripting Language — single JSON file.
2. **TMDL**: Tabular Model Definition Language — folder-based, human-readable.
3. **PBIX binary**: Power BI Desktop file format.
4. **XMLA commands**: Direct XMLA deployment via ADOMD.NET.

## Decision

Use **TMDL (folder format)** as the primary semantic model representation.

## Rationale

- **Human-readable**: Each table, measure, and relationship is a separate `.tmdl` file. Easy to review, diff, and version-control.
- **Git-friendly**: Folder-based structure works well with Git branching and pull requests.
- **Tooling support**: Tabular Editor 3, ALM Toolkit, and the PBI REST API all support TMDL.
- **Incremental changes**: Modify a single table or measure without regenerating the entire model.
- **Fabric Git integration**: Fabric workspaces support Git with TMDL as the native format.

## Consequences

- The Semantic Model Agent (Agent 04) generates TMDL folder output.
- Deployment uses the PBI REST API or XMLA endpoint to push TMDL.
- Developers need familiarity with TMDL syntax (vs. the BIM JSON format).
- Some older tools may not support TMDL — BIM export can be added as a fallback.

## File Structure

```
semantic_model/
├── model.tmdl
├── tables/
│   ├── Sales.tmdl
│   ├── Product.tmdl
│   └── Date.tmdl
├── relationships.tmdl
└── roles/
    └── RegionalManager.tmdl
```
