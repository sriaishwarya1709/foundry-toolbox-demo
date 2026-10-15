# Microsoft Foundry Toolbox demo: inline tools vs. Toolbox with tool search

This repo builds two **prompt agents** in Microsoft Foundry. They use the same model, the same instructions and the same tools. The only difference is how each agent gets its tools:

| Agent | How it gets tools | What the model sees on each turn |
|---|---|---|
| `travel-agent-inline` | Every tool is attached directly to the agent | All tool definitions (16 OpenAPI operations, MCP tools, Code Interpreter) |
| `travel-agent-toolbox` | One MCP connection to a **Foundry Toolbox** with **tool search** turned on | Only `tool_search` and `call_tool`. It searches for the tools it needs. |

Open both agents in the Foundry portal playground and run the same prompt in each. You can compare tool calls, token usage and latency side by side. You can also run `compare.py` to print the same comparison as a table.

```mermaid
flowchart LR
    subgraph A[travel-agent-inline]
      A1[gpt model] --> T1[weather] & T2[forecast] & T3[travel advisory] & T4[currency] & T5[holidays] & T6[... 16 ops] & T7[MS Learn MCP] & T8[Code Interpreter]
    end
    subgraph B[travel-agent-toolbox]
      B1[gpt model] --> MCP[Toolbox MCP endpoint]
      MCP --> S{{tool_search / call_tool}}
      S --> TB[(travel-toolbox:<br/>same tools, discovered on demand)]
    end
```

## Tools used

Every tool calls a free public API. None of them needs an API key.

| Type | Name | Backing API | Operations |
|---|---|---|---|
| OpenAPI | `weather` | wttr.in | current weather |
| OpenAPI | `geocoding` | Open-Meteo geocoding | city → lat/long, country, timezone |
| OpenAPI | `forecast` | Open-Meteo forecast | daily forecast |
| OpenAPI | `air_quality` | Open-Meteo air quality | current AQI, PM2.5, PM10, ozone |
| OpenAPI | `travel_advisory` | U.S. Department of State | advisory level (1–4) + summary |
| OpenAPI | `country_info` | World Bank | country profile, indicators (population, GDP) |
| OpenAPI | `currency` | Frankfurter (ECB) | latest rates, historical rates, currency list |
| OpenAPI | `holidays` | Nager.Date | public holidays, next holidays, long weekends, countries |
| OpenAPI | `world_time` | timeapi.io | current local time |
| MCP | `microsoft_learn` | Microsoft Learn MCP server | docs search / fetch / code samples |
| Built-in | `code_interpreter` | Foundry | run Python (calculations, charts) |
| Toolbox only | `toolbox_search` | Foundry | turns on tool search |

The OpenAPI specs live in [tools/openapi](tools/openapi). [catalog.py](catalog.py) is the single source of truth: it builds both the inline tool list and the toolbox tool list from those specs.

## Prerequisites

- An Azure subscription with a **Microsoft Foundry project** in a [region that supports toolboxes](https://learn.microsoft.com/azure/foundry/agents/concepts/limits-quotas-regions#tool-support-by-region-and-model).
- A chat model deployment in that project (tested with `gpt-5.4`).
- The **Foundry User** role on the project for the identity that runs the scripts.
- Python 3.10+ and the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli). Sign in with `az login`.

## Setup

```powershell
git clone https://github.com/sriaishwarya1709/foundry-toolbox-demo.git
cd foundry-toolbox-demo

python -m venv .venv
.\.venv\Scripts\Activate.ps1        # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

copy .env.example .env              # macOS/Linux: cp .env.example .env
# edit .env -> PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME
```

You can find `PROJECT_ENDPOINT` on your project's **Overview** page in the [Foundry portal](https://ai.azure.com). It looks like `https://<account>.services.ai.azure.com/api/projects/<project>`.

## Run the demo

```powershell
python setup_demo.py      # creates the toolbox + both agents
python verify_toolbox.py  # lists toolbox tools and tests tool_search
python compare.py         # runs the same prompts against both agents
```

> [!NOTE]
> Tool search indexes a new toolbox version in the background. Wait a few minutes after you run `setup_demo.py` before you test the toolbox agent.

You can pass your own prompts to `compare.py`:

```powershell
python compare.py "What's the weather and air quality in Delhi right now?"
```

### In the Foundry portal

1. Open your project at [ai.azure.com](https://ai.azure.com). Use the new Foundry experience.
2. Under **Build → Agents**, open `travel-agent-inline` and `travel-agent-toolbox` in two playground tabs.
3. Under **Build → Tools → Toolboxes**, open `travel-toolbox` to show the curated tools and the tool search setting.
4. Run the same prompt in both playgrounds. Compare the tool calls (`tool_search` → `call_tool` in the toolbox agent) and the token usage.
5. If Application Insights is connected to the project, open **Tracing** to see per-run tokens, latency and tool spans.

### Suggested prompts

| Shows | Prompt |
|---|---|
| Single tool | What's the weather in Paris right now? |
| Many OpenAPI tools | I'm flying to Tokyo next week. Is it safe to travel, what's the 5-day forecast, how many yen is 500 USD, and are there public holidays coming up? |
| MCP server | How do I enable tool search in a Microsoft Foundry toolbox? |
| Code Interpreter | Convert 1,200 USD to JPY, EUR and GBP and make a bar chart of the results. |
| Everything | Plan 4 days in Tokyo next week: check the safety advisory and forecast, convert a 2,000 USD budget to yen, chart daily spend with Python, and link the Azure docs for building a travel agent like you. |

## Sample results

Sample results from `compare.py` with `gpt-5.4`. Token counts vary from run to run.

| Prompt | Inline agent | Toolbox agent |
|---|---|---|
| Weather in Paris (one tool) | 2,727 tokens, 8.7 s | **1,620 tokens (−41%), 3.9 s** |
| Tokyo trip (4 capabilities) | 5,497 tokens | 11,949 tokens |
| Germany long weekends + USD→EUR | 3,385 tokens | 6,166 tokens |

How to read these results:

- **The toolbox keeps the starting context small.** The model sees two meta-tools instead of every tool definition. Simple, single-intent requests use fewer tokens and run faster.
- **Each tool search adds a model turn.** With only about 20 tools, the inline list is still cheap. A multi-step request can use more tokens through tool search than through inline tools.
- **Tool search pays off as the catalog grows.** The cost of inline tools rises with every tool you add. With tool search, the cost stays roughly flat. Microsoft recommends tool search for toolboxes with **10–15+ tools**. You can also [pin tools](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/tool-search#pin-critical-tools) that are used often.
- **Benefits beyond tokens:** define tools once and reuse them across agents and frameworks, manage credentials in one place, use versioning to promote a new default without redeploying agents, and apply guardrails at the toolbox level.

## How it works

- `setup_demo.py`
  - Creates a toolbox version with every tool plus `ToolSearchToolboxTool()`, then promotes it to the default version.
  - Creates the inline agent with `catalog.inline_tools()`.
  - Creates the toolbox agent with a single `MCPTool` that points to the toolbox's consumer endpoint, `{project}/toolboxes/{name}/mcp?api-version=v1`. That endpoint always serves the default version.
- `verify_toolbox.py` connects to the toolbox's MCP endpoint with the MCP Python SDK. With tool search on, it expects `tools/list` to return only `tool_search` and `call_tool`, and then runs a few searches.
- `compare.py` calls both agents through the Responses API. It prints tokens, latency and every tool call for each agent.
- `cleanup.py` deletes both agents and the toolbox.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No tools matched query ...` right after setup | The tool search index is still building. Wait a few minutes and retry. If one agent still fails while `verify_toolbox.py` succeeds, delete that agent and run `setup_demo.py` again. |
| `Multiple tools without identifiers found` | A toolbox allows only one unnamed tool, and `toolbox_search` already takes that slot. Give other built-in tools a `name`, as `catalog.py` does for Code Interpreter. |
| Travel advisory returns `[]` | The State Department API uses FIPS 10-4 codes, not ISO codes. For example, `JA` is Japan and `GM` is Germany. The tool description lists common codes. |
| `401`/`403` from the project | Assign the **Foundry User** role on the project, and make sure `az login` uses the project's tenant. |

## Cleanup

```powershell
python cleanup.py
```

## Learn more

- [What is Toolbox in Microsoft Foundry?](https://learn.microsoft.com/azure/foundry/agents/concepts/toolbox-overview)
- [Create and manage a toolbox](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/toolbox)
- [Enable tool search in a toolbox](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/tool-search)
- [OpenAPI tools](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/openapi) · [MCP tools](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/model-context-protocol)

> This is a sample for demonstration purposes. The public APIs it uses are third-party services with their own terms and availability.
