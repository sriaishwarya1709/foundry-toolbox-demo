"""Delete the demo agents and toolbox from the Foundry project."""

import os

from azure.ai.projects import AIProjectClient
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    project = AIProjectClient(
        endpoint=os.environ["PROJECT_ENDPOINT"], credential=DefaultAzureCredential(), allow_preview=True
    )
    for agent in (os.environ["INLINE_AGENT_NAME"], os.environ["TOOLBOX_AGENT_NAME"]):
        try:
            project.agents.delete(agent_name=agent)
            print(f"Deleted agent '{agent}'")
        except ResourceNotFoundError:
            print(f"Agent '{agent}' not found")
    try:
        project.toolboxes.delete(os.environ["TOOLBOX_NAME"])
        print(f"Deleted toolbox '{os.environ['TOOLBOX_NAME']}'")
    except ResourceNotFoundError:
        print(f"Toolbox '{os.environ['TOOLBOX_NAME']}' not found")


if __name__ == "__main__":
    main()
