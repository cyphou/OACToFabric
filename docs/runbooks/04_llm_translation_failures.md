# Runbook: Handling LLM Translation Failures

## When LLM Translation Fails

The hybrid translator (`src/core/hybrid_translator.py`) uses a **rules-first, LLM-fallback** strategy. LLM failures can occur due to:

1. **API errors** — Azure OpenAI unavailable or quota exceeded.
2. **Low confidence** — LLM output doesn't pass syntax validation.
3. **Unsupported patterns** — Expression too complex for the model.

---

## Step 1: Check the Translation Cache

The framework caches successful translations. Check if a previous run already translated the expression:

```python
from src.core.translation_cache import TranslationCache
cache = TranslationCache()
result = cache.lookup("source_expression_hash")
```

---

## Step 2: Review the LLM Response

Check logs for the specific translation attempt:

```
grep "translation_failed\|llm_error" output/run_001/*.log
```

Common error patterns:

| Error | Cause | Fix |
|---|---|---|
| `429 Rate Limit` | Token budget exhausted | Increase `token_budget_per_run` in config |
| `400 Content Filter` | Expression triggered content policies | Rephrase the input, remove sensitive column names |
| `Timeout` | Expression too long | Split complex expressions into sub-expressions |
| `Syntax validation failed` | LLM output had DAX/PySpark syntax errors | See Step 4 |

---

## Step 3: Add a Rule-Based Translation

If the pattern is common, add a deterministic rule instead of relying on LLM:

### For OAC Expression → DAX

Edit `src/agents/semantic/expression_translator.py`:

```python
# Add to the RULES dictionary
RULES["MY_FUNCTION(...)"] = "DAX_EQUIVALENT(...)"
```

### For PL/SQL → PySpark

Edit `src/agents/etl/plsql_translator.py`:

```python
# Add to the PL/SQL translation rules
PLSQL_RULES["CUSTOM_PROC(...)"] = "spark_equivalent(...)"
```

---

## Step 4: Manual Translation Workflow

For expressions that cannot be auto-translated:

1. **Export failed translations**:
   ```bash
   oac-migrate status --show-failures --output-format csv > failed_translations.csv
   ```

2. **Manually translate** each expression and add to an override file:
   ```json
   // config/manual_translations.json
   {
     "EVALUATE(CASE WHEN ...)": "IF(condition, then, else)",
     "NVL(col, 0)": "COALESCE(col, 0)"
   }
   ```

3. **Re-run migration** — the framework picks up manual overrides before calling LLM.

---

## Step 5: Improve LLM Accuracy

### Tune Prompts

Edit `src/core/prompt_templates.py`:
- Add more few-shot examples for the failing pattern.
- Adjust the system prompt for clarity.

### Adjust Parameters

In `config/migration.toml`:

```toml
[llm]
temperature = 0.05   # Lower = more deterministic
max_tokens = 4096    # Increase for complex expressions
max_retries = 5      # More retry attempts
```

### Validate with the Syntax Checker

```python
from src.core.syntax_validator import SyntaxValidator
validator = SyntaxValidator()
result = validator.validate_dax("CALCULATE(SUM(Sales[Amount]))")
print(result.valid, result.errors)
```

---

## Step 6: Bypass LLM Entirely

If LLM is unreliable for a migration run, disable it:

```toml
# config/migration.toml
[llm]
enabled = false
```

The framework will use only rule-based translations and flag unresolved expressions for manual review.

---

## Prevention

- **Curate few-shot examples**: Keep `prompt_templates.py` updated with real translations from each run.
- **Monitor token budget**: Check `items_migrated` vs `llm_tokens_used` metrics in Application Insights.
- **Cache aggressively**: Enable `cache_enabled = true` to avoid re-translating known expressions.
