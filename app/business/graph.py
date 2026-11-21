from rag_tools import get_tools, tool_node
from langchain_groq import ChatGroq
from app.state import State
from langgraph.graph import END, START, StateGraph
from functools import lru_cache

tools = get_tools()
llm = ChatGroq(model="openai/gpt-oss-120b")

llm_with_tools = llm.bind_tools(tools)

def agent(state: State):
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
def get_graph():
    graph_builder = StateGraph(State)

    graph_builder.add_node("tools", tool_node())
    graph_builder.add_node("agent", agent)

    graph_builder.add_edge(START, "agent")
    graph_builder.add_edge("tools", "agent")

    graph_builder.add_conditional_edges(
        "agent", route, {"tools": "tools", END: END}
    )

    return graph_builder.compile()