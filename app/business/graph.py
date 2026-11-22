from functools import lru_cache

from langchain_core.messages import AIMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph

from app.business.rag_tools import *
from app.state import State

MAX_TOOL_ROUNDS = 3

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    timeout=45,      # seconds per LLM call; without this a slow call blocks forever
    max_retries=1,   # default retries on 429s can look like a freeze
)
tools = get_tools()
llm_with_tools = llm.bind_tools(tools)   # bind once, not on every agent call

FORCE_FINAL = HumanMessage(
    "Tool budget is used up. Do not call any more tools. Return the final JSON now "
    "using only what you have found. Use match_status \"not_found\" or \"uncertain\" "
    "for anything unresolved."
)


def agent(state: State):
    mess = state["mess"]
    rounds = sum(1 for m in mess if isinstance(m, AIMessage) and m.tool_calls)

    if rounds >= MAX_TOOL_ROUNDS:
        # plain llm (no tools bound), so it cannot request another tool call
        return {"mess": [llm.invoke(mess + [FORCE_FINAL])]}

    return {"mess": [llm_with_tools.invoke(mess)]}


def route(state: State):
    mess = state.get("mess")
    if not mess:
        raise ValueError("No messages found in state")
    return "tools" if mess[-1].tool_calls else END


@lru_cache(maxsize=1)
def get_graph(tool_node):
    graph_builder = StateGraph(State)
    graph_builder.add_node("tools", tool_node())
    graph_builder.add_node("agent", agent)

    graph_builder.add_edge(START, "agent")
    graph_builder.add_edge("tools", "agent")
    graph_builder.add_conditional_edges("agent", route, {"tools": "tools", END: END})

    return graph_builder.compile()