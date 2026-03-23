# User Guide: Customizing Translation Rules

The migration framework translates OAC expressions and PL/SQL code to DAX and PySpark. You can customize the translation rules to handle your organization's specific patterns.

---

## Architecture

```
Input Expression
       │
       ▼
  Rule Engine (deterministic, fast)
       │
       ├── Match? → Return translation
       │
       └── No match → LLM Fallback (GPT-4)
                            │
                            └── Syntax Validate → Cache → Return
```

---

## 1. OAC Expression → DAX Rules

### Location

Rules are defined in `src/agents/semantic/expression_translator.py`.

### Adding a Rule

```python
# In the EXPRESSION_RULES dictionary
EXPRESSION_RULES = {
    # Pattern (regex) → DAX replacement
    r"SUM\((.+?)\)": r"SUM(\1)",
    r"COUNT\((.+?)\)": r"COUNTROWS(\1)",
    r"NVL\((.+?),\s*(.+?)\)": r"COALESCE(\1, \2)",

    # Add your custom rule:
    r"MY_CUSTOM_FUNC\((.+?)\)": r"CALCULATE(SUM(\1))",
}
```

### Testing Your Rule

```bash
python -m pytest tests/test_expression_translator.py -v -k "test_my_custom"
```

---

## 2. PL/SQL → PySpark Rules

### Location

Rules are defined in `src/agents/etl/plsql_translator.py`.

### Adding a Rule

```python
# In the PLSQL_RULES dictionary
PLSQL_RULES = {
    r"SYSDATE": "current_timestamp()",
    r"NVL\((.+?),\s*(.+?)\)": r"coalesce(\1, \2)",
    r"DECODE\((.+?),(.+?),(.+?),(.+?)\)": r"when(\1 == \2, \3).otherwise(\4)",

    # Add your custom rule:
    r"MY_PROC\((.+?)\)": r"my_spark_udf(\1)",
}
```

---

## 3. LLM Prompt Templates

### Location

Prompt templates are in `src/core/prompt_templates.py`.

### Adding Few-Shot Examples

To improve LLM translation accuracy, add real examples from your OAC environment:

```python
# In EXPRESSION_FEW_SHOT_EXAMPLES
EXPRESSION_FEW_SHOT_EXAMPLES = [
    {
        "input": "FILTER(\"Sales\".\"Region\" USING \"Geography\".\"Country\" = 'US')",
        "output": "CALCULATE(SUM(Sales[Amount]), Geography[Country] = \"US\")",
    },
    # Add your example:
    {
        "input": "YOUR_OAC_EXPRESSION_HERE",
        "output": "EXPECTED_DAX_OUTPUT_HERE",
    },
]
```

### Adjusting the System Prompt

```python
EXPRESSION_SYSTEM_PROMPT = """
You are an expert at translating Oracle Analytics Cloud (OAC) 
expressions to DAX (Data Analysis Expressions) for Power BI.

Rules:
- Preserve the semantic meaning exactly.
- Use standard DAX functions.
- Return ONLY the DAX expression, no explanation.

{additional_context}
"""
```

---

## 4. Syntax Validation

After translation (rule or LLM), the result passes through the syntax validator.

### Location

`src/core/syntax_validator.py`

### Adding Custom Validation

```python
# Add to DAX_VALIDATION_RULES
DAX_VALIDATION_RULES = [
    # Balanced parentheses
    lambda expr: expr.count("(") == expr.count(")"),
    # No PL/SQL remnants
    lambda expr: "NVL(" not in expr,
    # Add your rule:
    lambda expr: "FORBIDDEN_FUNCTION(" not in expr,
]
```

---

## 5. Translation Cache

Successful translations are cached to avoid re-translating identical expressions.

### Location

`src/core/translation_cache.py`

### Pre-populating the Cache

For known translations that should always be used:

```python
from src.core.translation_cache import TranslationCache

cache = TranslationCache()
cache.store(
    source_hash="hash_of_source_expression",
    source_expression="NVL(col, 0)",
    target_expression="COALESCE(col, 0)",
    translation_method="manual",
)
```

---

## 6. Manual Overrides

For expressions that can't be auto-translated, create a JSON override file:

```json
{
    "translations": [
        {
            "source": "EXACT_OAC_EXPRESSION",
            "target": "EXACT_DAX_EXPRESSION",
            "notes": "Why this translation is correct"
        }
    ]
}
```

Place it as `config/manual_translations.json`. The hybrid translator checks overrides before calling the LLM.

---

## Testing Best Practices

1. **Unit test each rule** with exact input/output assertions.
2. **Integration test** with real OAC export samples.
3. **Measure coverage**: Track `rule_match_rate` to see what percentage of expressions are handled by rules vs. LLM.
4. **Review LLM outputs**: Periodically audit cached LLM translations for correctness and convert high-quality ones into rules.
