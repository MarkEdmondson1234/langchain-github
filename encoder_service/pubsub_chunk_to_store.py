# imports
import os
from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
import base64

from langchain.vectorstores import SupabaseVectorStore
from supabase import Client, create_client
from dotenv import load_dotenv
import hashlib
from langchain.schema import Document
import logging

load_dotenv()

def compute_sha1_from_content(content):
    readable_hash = hashlib.sha1(content).hexdigest()
    return readable_hash


def pubsub_chunk_to_store(data: dict, vector_name:str="documents"):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Will only attempt to send one chunk to vectorstore.  For bigger documents use pubsub_to_store.py
    Args:
         data JSON
    """
    message_data = base64.b64decode(data['message']['data']).decode('utf-8')
    attributes = data['message'].get('attributes', {})
    messageId = data['message'].get('messageId')
    publishTime = data['message'].get('publishTime')

    print(f"This Function was triggered by messageId {messageId} published at {publishTime}")

    print(f"Message data: {message_data}")

    metadata = attributes

    hash = compute_sha1_from_content(message_data)
    metadata["file_sha1"] = hash
    metadata["type"] = "message"
    doc = Document(page_content=message_data, metadata=metadata)

    logging.info("Initiating Supabase store")
    # init embedding and vector store
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    logging.info(f"Supabase URL: {supabase_url}")
    embeddings = OpenAIEmbeddings()
    supabase: Client = create_client(supabase_url, supabase_key)

    vector_store = SupabaseVectorStore(supabase, embeddings, table_name=vector_name)

    logging.info("Adding single document to Supabase")
    vector_store.add_documents([doc])

    logging.info(f"Added doc with metadata: {metadata}")

    return metadata
