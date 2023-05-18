#!/Users/mark/dev/ml/langchain/read_github/langchain_github/env/bin/python
# change above to the location of your local Python venv installation

import os
import my_llm.standards as my_llm
import openai
from langchain.chat_models import ChatOpenAI
from my_llm.langchain_class import PubSubChatMessageHistory
# imports
import os, shutil
import pathlib
from langchain.document_loaders.unstructured import UnstructuredFileLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
from google.cloud import storage
import base64
import json
import langchain.text_splitter as text_splitter

from langchain.vectorstores import SupabaseVectorStore
from supabase import Client, create_client
from dotenv import load_dotenv
import tempfile
import hashlib
from langchain.schema import Document
import logging

supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

print(f"Supabase settings: {supabase_url} {supabase_key}")
embeddings = OpenAIEmbeddings()
print("Creating client")
supabase: Client = create_client(supabase_url, supabase_key)

print("Initiating vectorstore")
vector_store = SupabaseVectorStore(supabase, embeddings, table_name="documents")

chunks = [Document(page_content="debugging1"), Document(page_content="debugging2")]

vector_store.add_documents(chunks)

print("Added texts")

