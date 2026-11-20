from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict

class State(TypedDict):
    mess: Annotated[list, add_messages]