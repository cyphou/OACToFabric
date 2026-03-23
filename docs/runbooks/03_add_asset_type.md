# Runbook: Adding a New Asset Type

## Overview

The migration framework supports custom OAC asset types beyond the 14 built-in types. Follow this guide to add support for a new asset type end-to-end.

---

## Step 1: Add the Enum Value

Edit `src/core/models.py`:

```python
class AssetType(str, Enum):
    # ... existing types ...
    MY_NEW_TYPE = "myNewType"     # Add here
```

---

## Step 2: Update the Discovery Agent

### If from RPD XML

Add a parser method in `src/agents/discovery/rpd_parser.py`:

```python
def _parse_my_new_type(self) -> list[InventoryItem]:
    """Extract MyNewType objects from RPD XML."""
    items = []
    for elem in self._tree.iter("MyNewTypeElement"):
        name = _attr(elem, "name")
        items.append(InventoryItem(
            id=_id("myNewType", name),
            asset_type=AssetType.MY_NEW_TYPE,
            source_path=f"/myNewTypes/{name}",
            name=name,
            metadata={...},  # extract relevant attributes
        ))
    return items
```

Call it from `parse()`:

```python
items.extend(self._parse_my_new_type())
```

### If from OAC REST API

Add a method in `src/clients/oac_catalog.py`:

```python
async def list_my_new_types(self) -> list[dict]:
    return await self._get("/api/v1/myNewTypes")
```

And wire it into `src/agents/discovery/oac_client.py`.

---

## Step 3: Add Migration Logic

Choose the appropriate agent for migration:
- **Schema-level**: Add to Agent 02 (`schema_agent.py`)
- **ETL-level**: Add to Agent 03 (`etl_agent.py`)
- **Semantic-level**: Add to Agent 04 (`semantic_agent.py`)
- **Report-level**: Add to Agent 05 (`report_agent.py`)

Example for Agent 02:

```python
# In schema_agent.py — extend the execute() method
async def _migrate_my_new_type(self, item: InventoryItem) -> bool:
    """Migrate a MyNewType asset to Fabric."""
    # Translation logic here
    return True
```

---

## Step 4: Add Validation Rules

Extend Agent 07 in `src/agents/validation/`:

```python
# In the appropriate validator (data_reconciliation.py, semantic_validator.py, etc.)
def _validate_my_new_type(self, source_item, target_item) -> ValidationCheck:
    ...
```

---

## Step 5: Add Tests

Create test cases in the appropriate test file:

```python
# tests/test_my_new_type.py
def test_discovers_my_new_type():
    ...

def test_migrates_my_new_type():
    ...

def test_validates_my_new_type():
    ...
```

---

## Step 6: Update Configuration

If the new type requires special settings, add a section to `config/migration.toml`:

```toml
[my_new_type]
batch_size = 100
custom_setting = "value"
```

---

## Checklist

- [ ] `AssetType` enum updated
- [ ] Discovery parser/client extended
- [ ] Migration agent handles the new type
- [ ] Validation rules added
- [ ] Unit tests written and passing
- [ ] Integration tests cover the new type
- [ ] Configuration documented
