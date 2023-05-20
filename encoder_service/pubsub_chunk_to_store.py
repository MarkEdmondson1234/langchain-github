# imports
import os
from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
import base64
import json

from langchain.vectorstores import SupabaseVectorStore
from supabase import Client, create_client
from dotenv import load_dotenv
from langchain.schema import Document
import logging

load_dotenv()

def from_pubsub_to_supabase(data: dict, vector_name:str):
    """Triggered from a message on a Cloud Pub/Sub topic "embed_chunk" topic
    Will only attempt to send one chunk to vectorstore.  For bigger documents use pubsub_to_store.py
    Args:
         data JSON
    """

    logging.info(f"vectorstore: {vector_name}")

    #file_sha = data['message']['data']

    message_data = base64.b64decode(data['message']['data']).decode('utf-8')
    messageId = data['message'].get('messageId')
    publishTime = data['message'].get('publishTime')

    logging.debug(f"This Function was triggered by messageId {messageId} published at {publishTime}")
    logging.debug(f"from_pubsub_to_supabase message data: {message_data}")

    the_json = json.loads(message_data)

    if not isinstance(the_json, dict):
        raise ValueError(f"Could not parse message_data from json to a dict: got {message_data} or type: {type(the_json)}")

    page_content = the_json.get("page_content", None)
    if page_content is None:
        return "No page content"
    
    metadata = the_json.get("metadata", None)

    doc = Document(page_content=page_content, metadata=metadata)

    logging.debug("Initiating Supabase store")
    # init embedding and vector store
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    logging.info(f"Supabase URL: {supabase_url}")
    embeddings = OpenAIEmbeddings()
    supabase: Client = create_client(supabase_url, supabase_key)

    # ensure the supabase sql function and table has been created before using this
    vector_store = SupabaseVectorStore(supabase, embeddings, 
                                       table_name=vector_name,
                                       query_name=f"match_documents_{vector_name}")

    logging.debug("Adding single document to Supabase")
    vector_store.add_documents([doc])

    logging.info(f"Added doc with metadata: {metadata}")

    return metadata
