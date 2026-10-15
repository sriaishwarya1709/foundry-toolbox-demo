"""Run the same prompts against both agents and compare tokens, latency and tool calls."""

import json
import os
import sys
import time

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()
AGENTS = [os.environ["INLINE_AGENT_NAME"], os.environ["TOOLBOX_AGENT_NAME"]]

PROMPTS = [
    "What's the weather in Paris right now?",
    "I'm flying to Tokyo next week. Is it safe to travel, what's the 5-day forecast, "
    "how many yen is 500 USD, and are there public holidays coming up?",
    "Find the long weekends in Germany in 2026 and tell me the current USD to EUR rate.",
]


def describe_tool_calls(output) -> list[str]:
    calls = []
    for item in output:
        if item.type in ("message", "reasoning", "mcp_list_tools") or item.type.endswith("_output"):
            continue
        name = getattr(item, "name", None) or item.type
        if name == "call_tool":
            name = f"call_tool -> {json.loads(item.arguments or '{}').get('name', '?')}"
        elif name == "tool_search":
            name = f"tool_search('{json.loads(item.arguments or '{}').get('query', '')}')"
        calls.append(name)
    return calls


def run(openai, agent: str, prompt: str) -> dict:
    start = time.perf_counter()
    response = openai.responses.create(
        input=prompt, extra_body={"agent_reference": {"name": agent, "type": "agent_reference"}}
    )
    usage = response.usage
    return {
        "agent": agent,
        "seconds": round(time.perf_counter() - start, 1),
        "input": usage.input_tokens,
        "output": usage.output_tokens,
        "total": usage.total_tokens,
        "tools": describe_tool_calls(response.output),
        "answer": response.output_text,
    }


def main() -> None:
    prompts = sys.argv[1:] or PROMPTS
    project = AIProjectClient(
        endpoint=os.environ["PROJECT_ENDPOINT"], credential=DefaultAzureCredential(), allow_preview=True
    )
    openai = project.get_openai_client()
    totals = {a: 0 for a in AGENTS}

    for i, prompt in enumerate(prompts, 1):
        print(f"\n=== Prompt {i}: {prompt}")
        for agent in AGENTS:
            try:
                r = run(openai, agent, prompt)
            except Exception as ex:  # keep the side-by-side going if one agent fails
                print(f"\n[{agent}] ERROR: {ex}")
                continue
            totals[agent] += r["total"]
            print(f"\n[{agent}] {r['seconds']}s | input {r['input']} | output {r['output']} | total {r['total']}")
            for call in r["tools"]:
                print(f"   - {call}")
            print("   " + r["answer"].replace("\n", "\n   ")[:600])

    print("\n=== Total tokens across all prompts")
    for agent, total in totals.items():
        print(f"  {agent:<28} {total:>8}")


if __name__ == "__main__":
    main()
