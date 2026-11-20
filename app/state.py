from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from typing import Annotated

class State(StateGraph):
    message: Annotated[list, add_messages]