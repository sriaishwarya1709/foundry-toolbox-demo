"""Single source of truth for the demo tools, rendered either inline or as a toolbox."""

import json
from pathlib import Path

from azure.ai.projects.models import (
    CodeInterpreterTool,
    CodeInterpreterToolboxTool,
    MCPTool,
    MCPToolboxTool,
    OpenApiAnonymousAuthDetails,
    OpenApiFunctionDefinition,
    OpenApiTool,
    OpenApiToolboxTool,
    ToolSearchToolboxTool,
)

SPEC_DIR = Path(__file__).parent / "tools" / "openapi"

# (tool name, spec file, description used for model selection and tool search ranking)
OPENAPI_TOOLS = [
    ("weather", "weather.json", "Current weather conditions (temperature, wind, sky) for a city."),
    ("geocoding", "geocoding.json", "Convert a city name into latitude/longitude, country code and timezone."),
    ("forecast", "forecast.json", "Multi-day weather forecast: daily min/max temperature and rain for coordinates."),
    ("air_quality", "air_quality.json", "Current air quality index (AQI), PM2.5, PM10 and ozone for coordinates."),
    ("travel_advisory", "travel_advisory.json", "US State Department travel advisory level (1-4) and safety summary for a country."),
    ("country_info", "country_info.json", "Country profile (capital, region, income level) plus population and GDP indicators."),
    ("currency", "currency.json", "Currency exchange rates and money conversion (latest or historical)."),
    ("holidays", "holidays.json", "Public holidays, upcoming holidays and long weekends for a country."),
    ("world_time", "world_time.json", "Current local date and time in a timezone."),
]

MSLEARN_MCP = {
    "server_label": "microsoft_learn",
    "server_url": "https://learn.microsoft.com/api/mcp",
    "server_description": "Search and fetch official Microsoft and Azure documentation and code samples.",
}


def _openapi_definition(name: str, spec_file: str, description: str) -> OpenApiFunctionDefinition:
    spec = json.loads((SPEC_DIR / spec_file).read_text(encoding="utf-8"))
    return OpenApiFunctionDefinition(
        name=name, description=description, spec=spec, auth=OpenApiAnonymousAuthDetails()
    )


def inline_tools() -> list:
    """Tools attached directly to the agent - every definition is sent to the model each turn."""
    tools: list = [OpenApiTool(openapi=_openapi_definition(*t)) for t in OPENAPI_TOOLS]
    tools.append(MCPTool(require_approval="never", **MSLEARN_MCP))
    tools.append(CodeInterpreterTool())
    return tools


def toolbox_tools(tool_search: bool = True) -> list:
    """Same tools packaged for a Foundry toolbox, optionally fronted by tool search."""
    tools: list = [OpenApiToolboxTool(openapi=_openapi_definition(*t)) for t in OPENAPI_TOOLS]
    tools.append(MCPToolboxTool(require_approval="never", **MSLEARN_MCP))
    # Toolbox allows only one unnamed tool; toolbox_search is always unnamed.
    tools.append(
        CodeInterpreterToolboxTool(
            name="code_interpreter",
            description="Run Python to calculate budgets, convert units, or build tables and charts.",
        )
    )
    if tool_search:
        tools.append(ToolSearchToolboxTool())
    return tools
