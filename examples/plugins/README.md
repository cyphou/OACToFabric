# Plugin Examples

Sample plugins demonstrating the OAC-to-Fabric extensibility architecture.

## Files

| File | Type | Description |
|------|------|-------------|
| `custom_connector_example.py` | ConnectorPlugin | Custom source connector for SAP BW |
| `custom_translation_rules.yaml` | TranslationRuleSet | Custom OAC→DAX translation rules |
| `plugin.toml` | PluginManifest | Plugin metadata and configuration |

## Plugin Types

The framework supports three plugin types:

1. **TranslationPlugin** — Add custom expression translation rules (OAC→DAX, PL/SQL→PySpark)
2. **AgentPlugin** — Register a custom agent in the orchestration DAG
3. **ConnectorPlugin** — Add a new source platform connector

## Usage

### Register a plugin via CLI

```bash
oac-migrate marketplace install ./examples/plugins/
```

### Register programmatically

```python
from src.plugins.plugin_manager import PluginManager, PluginManifest

manager = PluginManager()

manifest = PluginManifest(
    name="sap-bw-connector",
    version="1.0.0",
    description="SAP BW source connector",
    entry_point="examples.plugins.custom_connector_example:SAPBWConnectorPlugin",
)
```

## Creating Your Own Plugin

1. Create a `plugin.toml` with metadata
2. Subclass the appropriate plugin base (`ConnectorPlugin`, `TranslationPlugin`, or `AgentPlugin`)
3. Implement the required methods
4. Place in a directory and register via the CLI or marketplace
