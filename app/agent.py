from app.business.graph import *
from app.business.run_agent import *
from app.business.rag_tools import *

def answer_question(user_input: str):
    graph = get_graph(tool_node)
    return ask(graph, user_input)