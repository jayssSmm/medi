
from app.business.rag_tools import *
from langchain_groq import ChatGroq
from app.state import State
from langgraph.graph import END, START, StateGraph
from functools import lru_cache

llm = ChatGroq(model="openai/gpt-oss-120b")
tools = get_tools()

def agent(state: State):
    llm_with_tools = llm.bind_tools(tools)
    return {"mess": [llm_with_tools.invoke(state['mess'])]}

def route(state: State):
    mess = state.get('mess', None)

    if not mess:
        raise ValueError("No messages found in state")

    mess = mess[-1]

    if mess.tool_calls:
        return "tools"

    return END

    
@lru_cache(maxsize=1)
def get_graph(tool_node):
    graph_builder = StateGraph(State)

    graph_builder.add_node("tools", tool_node())
    graph_builder.add_node("agent", agent)

    graph_builder.add_edge(START, "agent")
    graph_builder.add_edge("tools", "agent")

    graph_builder.add_conditional_edges(
        "agent", route, {"tools": "tools", END: END}
    )

    return graph_builder.compile()