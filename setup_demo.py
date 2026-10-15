"""Create the travel toolbox and the two side-by-side prompt agents (inline tools vs toolbox)."""

import os

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

import catalog

load_dotenv()
ENDPOINT = os.environ["PROJECT_ENDPOINT"].rstrip("/")
MODEL = os.environ["MODEL_DEPLOYMENT_NAME"]
TOOLBOX = os.environ["TOOLBOX_NAME"]
INLINE_AGENT = os.environ["INLINE_AGENT_NAME"]
TOOLBOX_AGENT = os.environ["TOOLBOX_AGENT_NAME"]

BASE_INSTRUCTIONS = """You are a concise travel-planning assistant.
Always ground answers in your tools: weather, forecast, air quality, US travel advisories,
country facts, currency rates, public holidays and local time. Never guess live data.
Answer in short bullet points and name the data source for each fact."""

TOOL_SEARCH_HINT = """
Your tools are discovered on demand: call `tool_search`, then invoke the returned tool through
`call_tool`. Search for ONE capability per query using 1-3 keywords (for example 'weather',
'forecast', 'currency exchange', 'travel advisory', 'public holidays', 'geocoding').
Call `tool_search` several times when a request needs several capabilities."""


def create_toolbox(project: AIProjectClient) -> str:
    version = project.toolboxes.create_version(
        name=TOOLBOX,
        description="Travel planning tools (weather, advisories, currency, holidays, ...) with tool search.",
        tools=catalog.toolbox_tools(tool_search=True),
    )
    # New versions of an existing toolbox are not promoted automatically.
    project.toolboxes.update(TOOLBOX, default_version=version.version)
    print(f"Toolbox '{version.name}' version {version.version} is now default")
    return f"{ENDPOINT}/toolboxes/{TOOLBOX}/mcp?api-version=v1"


def create_agents(project: AIProjectClient, toolbox_url: str) -> None:
    inline = project.agents.create_version(
        agent_name=INLINE_AGENT,
        description="Travel agent with every tool attached inline (no toolbox).",
        definition=PromptAgentDefinition(
            model=MODEL, instructions=BASE_INSTRUCTIONS, tools=catalog.inline_tools()
        ),
    )
    print(f"Agent '{inline.name}' v{inline.version} ({len(catalog.inline_tools())} inline tool entries)")

    toolbox = project.agents.create_version(
        agent_name=TOOLBOX_AGENT,
        description="Travel agent consuming the Foundry toolbox (tool search enabled).",
        definition=PromptAgentDefinition(
            model=MODEL,
            instructions=BASE_INSTRUCTIONS + TOOL_SEARCH_HINT,
            tools=[
                # Same-project toolbox: the agent runtime authenticates to it, no connection needed.
                MCPTool(server_label="travel_toolbox", server_url=toolbox_url, require_approval="never")
            ],
        ),
    )
    print(f"Agent '{toolbox.name}' v{toolbox.version} (1 toolbox MCP endpoint)")


def main() -> None:
    project = AIProjectClient(endpoint=ENDPOINT, credential=DefaultAzureCredential(), allow_preview=True)
    toolbox_url = create_toolbox(project)
    create_agents(project, toolbox_url)
    print("Tool search indexes the new toolbox version in the background - wait a few minutes before testing.")


if __name__ == "__main__":
    main()
