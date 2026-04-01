"""Tool registry — typed tool definitions exposed to the LLM reasoning loop.

Each tool wraps an existing agent method so the LLM can invoke concrete
migration actions.  Tools are declared with a JSON‑Schema–style parameter
definition, enabling the LLM to construct valid calls and the runtime to
validate inputs before execution.

Usage::

    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="translate_expression",
        description="Translate an OAC expression to DAX.",
        parameters={"expression": ToolParameter(type="string", description="OAC expression")},
        handler=my_translator.translate,
    ))

    result = await registry.invoke("translate_expression", {"expression": "@SUM(Sales)"})
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Parameter / tool schema
# ---------------------------------------------------------------------------


@dataclass
class ToolParameter:
    """A single parameter for a tool."""

    type: str = "string"  # string, integer, number, boolean, array, object
    description: str = ""
    required: bool = True
    enum: list[str] | None = None
    default: Any = None


@dataclass
class ToolDefinition:
    """A tool that the LLM can invoke.

    ``handler`` is an async callable that performs the actual work.
    ``agent_scope`` restricts which agents can use this tool (empty = all).
    """

    name: str
    description: str
    parameters: dict[str, ToolParameter] = field(default_factory=dict)
    return_type: str = "string"
    handler: Callable[..., Any] | Callable[..., Awaitable[Any]] | None = None
    agent_scope: list[str] = field(default_factory=list)

    def to_llm_schema(self) -> dict[str, Any]:
        """Emit an OpenAI function-calling–compatible JSON schema."""
        props: dict[str, Any] = {}
        required: list[str] = []
        for pname, param in self.parameters.items():
            prop: dict[str, Any] = {"type": param.type, "description": param.description}
            if param.enum:
                prop["enum"] = param.enum
            props[pname] = prop
            if param.required:
                required.append(pname)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                },
            },
        }


# ---------------------------------------------------------------------------
# Invocation result
# ---------------------------------------------------------------------------


@dataclass
class ToolResult:
    """Result of invoking a tool."""

    tool_name: str
    success: bool
    output: Any = None
    error: str = ""


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Registry of tools available to the LLM.

    Supports agent-scoped filtering so each agent only sees the tools it
    owns or is allowed to use.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    # ---- registration ----

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        if tool.name in self._tools:
            logger.warning("Overwriting tool '%s'", tool.name)
        self._tools[tool.name] = tool
        logger.debug("Registered tool '%s'", tool.name)

    def register_function(
        self,
        name: str,
        handler: Callable[..., Any],
        *,
        description: str = "",
        agent_scope: list[str] | None = None,
    ) -> ToolDefinition:
        """Convenience: auto-build a ToolDefinition from a callable's signature."""
        sig = inspect.signature(handler)
        params: dict[str, ToolParameter] = {}
        for pname, p in sig.parameters.items():
            if pname == "self":
                continue
            ptype = "string"
            ann = p.annotation
            if ann is not inspect.Parameter.empty:
                type_map = {int: "integer", float: "number", bool: "boolean", str: "string"}
                # Python 3.14+ may return string annotations (PEP 649)
                str_type_map = {"int": "integer", "float": "number", "bool": "boolean", "str": "string"}
                ptype = type_map.get(ann) or str_type_map.get(str(ann), "string")
            params[pname] = ToolParameter(
                type=ptype,
                required=p.default is inspect.Parameter.empty,
                default=None if p.default is inspect.Parameter.empty else p.default,
            )

        tool = ToolDefinition(
            name=name,
            description=description or (handler.__doc__ or "").strip().split("\n")[0],
            parameters=params,
            handler=handler,
            agent_scope=agent_scope or [],
        )
        self.register(tool)
        return tool

    # ---- lookup ----

    def get(self, name: str) -> ToolDefinition:
        """Get a tool by name.  Raises KeyError if not found."""
        if name not in self._tools:
            available = ", ".join(sorted(self._tools))
            raise KeyError(f"Tool '{name}' not found.  Available: {available}")
        return self._tools[name]

    def list_tools(self, *, agent_id: str = "") -> list[ToolDefinition]:
        """List tools, optionally filtered to those accessible by *agent_id*."""
        tools = list(self._tools.values())
        if agent_id:
            tools = [
                t for t in tools
                if not t.agent_scope or agent_id in t.agent_scope
            ]
        return tools

    def to_llm_tools(self, *, agent_id: str = "") -> list[dict[str, Any]]:
        """Return the tool list in OpenAI function-calling JSON format."""
        return [t.to_llm_schema() for t in self.list_tools(agent_id=agent_id)]

    def has(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    # ---- invocation ----

    async def invoke(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        """Invoke a tool by name with the given arguments.

        Handles both sync and async handlers.
        """
        try:
            tool = self.get(name)
        except KeyError as e:
            return ToolResult(tool_name=name, success=False, error=str(e))

        if tool.handler is None:
            return ToolResult(
                tool_name=name, success=False,
                error=f"Tool '{name}' has no handler",
            )

        # Validate required parameters
        for pname, param in tool.parameters.items():
            if param.required and pname not in arguments:
                return ToolResult(
                    tool_name=name, success=False,
                    error=f"Missing required parameter: '{pname}'",
                )

        try:
            result = tool.handler(**arguments)
            if inspect.isawaitable(result):
                result = await result
            return ToolResult(tool_name=name, success=True, output=result)
        except Exception as exc:
            logger.warning("Tool '%s' failed: %s", name, exc)
            return ToolResult(tool_name=name, success=False, error=str(exc))
