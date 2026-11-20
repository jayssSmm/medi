'''
this file serves the purpose of loading the generic medicine dataset's 
embeddings into qdrant
'''

from langchain_huggingface import HuggingFaceEmbeddings
import pandas as pd
from langchain_community.document_loaders import DataFrameLoader
from langchain_core.documents import Document
from qdrant_client import QdrantClient
import torch
from dotenv import load_dotenv
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer
from langchain_qdrant import QdrantVectorStore

load_dotenv()

qdrant_key = os.getenv("QDRANT_API_KEY")
qdrant_url = os.getenv("QDRANT_CLUSTER_URL")

df = pd.read_csv(
    "../../dataset/Product List_20_11_2026 @ 13_10_8.csv",
).fillna("")

df["text"] = (
    df["Generic Name"].astype(str)
    + ". " + df["Unit Size"].astype(str)
    + ". " + df["Group Name"].astype(str)
)

docs = DataFrameLoader(df, page_content_column="text").load()

def preprocess_dataset(docs_list):
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3.8-27B")

    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tokenizer,
        chunk_size=115,
        chunk_overlap=0,
    )

    return text_splitter.split_documents(docs_list)

doc_splits = preprocess_dataset(docs)

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

qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_key)

collection_name = 'generic medicines'

if qdrant_client.collection_exists(collection_name):
    vectorstore = QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        url=qdrant_url,
        api_key=qdrant_key,
        collection_name=collection_name,
    )
    print("\nDatasets already exists in Qdrant")
else:
    vectorstore = QdrantVectorStore.from_documents(
        doc_splits,
        embedding=embeddings,
        url=qdrant_url,
        api_key=qdrant_key,
        collection_name=collection_name,
    )