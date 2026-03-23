# ADR-002: Rules-First, LLM-Fallback Translation Strategy

## Status

**Accepted** — 2025-01

## Context

Migrating OAC expressions (calculation definitions, filters, prompts) to DAX/PySpark requires translation. Two approaches:

1. **Pure rule-based**: Deterministic regex/AST transformations.
2. **Pure LLM**: Send every expression to Azure OpenAI GPT-4.
3. **Hybrid**: Apply rules first, use LLM only for unmatched patterns.

## Decision

Use a **hybrid rules-first, LLM-fallback** strategy.

## Rationale

- **Deterministic core**: ~70% of expressions follow known patterns (SUM, COUNT, CASE WHEN, NVL, etc.) that can be translated reliably with rules.
- **LLM for the long tail**: Complex nested expressions, custom functions, and unusual patterns are handled by GPT-4 with few-shot examples.
- **Cost control**: LLM calls are expensive ($0.03/1K tokens for GPT-4). Rules-first minimizes token budget consumption.
- **Predictability**: Rule-based translations are deterministic — same input always produces same output. LLM translations may vary.
- **Syntax validation**: All translations (rule or LLM) pass through a syntax validator before acceptance.
- **Caching**: LLM results are cached to avoid re-translating identical expressions.

## Implementation

```
Input Expression
       │
       ▼
  ┌─────────────┐
  │ Rule Engine  │──── Match? ──── Yes ──► Return translation
  └─────────────┘                  No
       │                            │
       ▼                            ▼
  ┌─────────────┐            ┌─────────────┐
  │ Cache Check │── Hit? ──► │Return cached │
  └─────────────┘   Miss     └─────────────┘
       │
       ▼
  ┌─────────────┐
  │ LLM (GPT-4) │──► Syntax Validate ──► Cache ──► Return
  └─────────────┘
```

## Consequences

- Need to maintain both rule definitions and prompt templates.
- LLM translations require network access (Azure OpenAI endpoint).
- Migration can run without LLM (`llm.enabled = false`), flagging unresolved expressions.
- Translation accuracy depends on quality of few-shot examples.

## Metrics

- Track `rule_match_rate`, `llm_call_count`, `syntax_validation_pass_rate`.
- Target: ≥ 90% of expressions translated without manual intervention.
