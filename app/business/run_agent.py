from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.errors import GraphRecursionError
import json

from app.system_prompts.generic_prompt import GENERIC_AGENT_PROMPT


def print_trace(messages):
    """Print every message in the finished state, in order."""
    for i, m in enumerate(messages):
        if isinstance(m, HumanMessage):
            print(f"[{i}] USER: {m.content}")
        elif isinstance(m, AIMessage):
            for call in m.tool_calls:
                print(f"[{i}] AGENT -> calls {call['name']} {call['args']}")
            if m.content:
                print(f"[{i}] AGENT says: {m.content}")
        elif isinstance(m, ToolMessage):
            print(f"[{i}] TOOL {m.name} returned {len(m.content)} chars")
            print(f"     preview: {m.content[:200]!r}")


def ask(graph, medicines: list[dict], debug: bool = False) -> str:
    payload = json.dumps(
        [{"name": m.name, "strength": m.strength, "form": m.form} for m in medicines],
        ensure_ascii=False,
    )
    try:
        result = graph.invoke(
            {"mess": [
                ("system", GENERIC_AGENT_PROMPT),
                ("user", payload),
            ]},
            {"recursion_limit": 10 + 5 * len(medicines)},
        )
    except GraphRecursionError:
        return "Agent hit the step limit (probably looping on tool calls)."

    if debug:
        print_trace(result["messages"])

    return result["messages"][-1].content


if __name__ == "__main__":
    print(ask("In the Transformers library, are there any multilingual models?", debug=True))