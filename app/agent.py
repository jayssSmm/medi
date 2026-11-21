from app.business.graph import *
from app.business.run_agent import *

def answer_question(user_input: str):
    graph = get_graph()
    return ask(graph, user_input)