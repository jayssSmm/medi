from functools import lru_cache

from dotenv import load_dotenv
import os
import torch

from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain_core.tools.retriever import create_retriever_tool
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

from langchain_core.messages import SystemMessage

SYSTEM = SystemMessage(
    # TODO
)

@tool("web_search_tool")
def search_tool(query: str) -> str:
    """Search the web with DuckDuckGo and return the top results."""
    wrapper = DuckDuckGoSearchAPIWrapper(region="us-en", max_results=5)
    search = DuckDuckGoSearchResults(max_results=3, output_format="list")
    results = search.invoke(query)
    return "\n\n".join(
        f"{r['title']}\n{r['link']}\n{r['snippet']}"
        for r in results
    )


@lru_cache(maxsize=1)
def get_tools():
    load_dotenv()

    qdrant_key = os.getenv("QDRANT_API_KEY")
    qdrant_url = os.getenv("QDRANT_CLUSTER_URL")
    collection_name = "generic medicines"

    if not qdrant_url or not qdrant_key:
        raise ValueError("QDRANT_CLUSTER_URL and QDRANT_API_KEY must be set")

    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        # fall back to CPU when there is no GPU instead of crashing
        model_kwargs={"device": "cuda" if torch.cuda.is_available() else "cpu"},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 64},
        query_encode_kwargs={
            "normalize_embeddings": True,  # keep queries normalized like the documents
            "prompt": "Represent this sentence for searching relevant passages: ",
        },
    )

    client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
    if not client.collection_exists(collection_name):
        raise ValueError(f"Collection {collection_name!r} not found")

    vectorstore = QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        url=qdrant_url,
        api_key=qdrant_key,
        collection_name=collection_name,
    )

    retriever_tool = create_retriever_tool(
        vectorstore.as_retriever(),
        "retriever_generic_medicines",
        "Search Indian generic medicines for generic name, unit size, and group name.",
    )

    return [search_tool, retriever_tool]


def tool_node():
    return ToolNode(get_tools())