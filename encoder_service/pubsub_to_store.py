# imports
import os, shutil
import pathlib
from langchain.document_loaders.unstructured import UnstructuredFileLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document
from google.cloud import storage
import base64
import langchain.text_splitter as text_splitter

from langchain.vectorstores import SupabaseVectorStore
from supabase import Client, create_client
from dotenv import load_dotenv
import tempfile
import hashlib
from langchain.schema import Document
import logging

load_dotenv()

# utility functions
def convert_to_txt(file_path):
    file_dir, file_name = os.path.split(file_path)
    file_base, file_ext = os.path.splitext(file_name)
    txt_file = os.path.join(file_dir, f"{file_base}.txt")
    shutil.copyfile(file_path, txt_file)
    return txt_file

def compute_sha1_from_file(file_path):
    with open(file_path, "rb") as file:
        bytes = file.read() 
        readable_hash = hashlib.sha1(bytes).hexdigest()
    return readable_hash

def compute_sha1_from_content(content):
    readable_hash = hashlib.sha1(content).hexdigest()
    return readable_hash

# if message_data is a gcs:// filepath, download that file from google cloud storage
#  and parse it using below
def read_file_to_document(gs_file: pathlib.Path, split=False, metadata: dict = None):
    if not gs_file.is_file():
        raise ValueError(f"{gs_file.filename} is not a valid file")
    
    file_sha1 = compute_sha1_from_file(gs_file.name)
    
    try:
        loader = UnstructuredFileLoader(gs_file)
        if split:
            # only supported for some file types
            docs = loader.load_and_split()
        else:
            docs = loader.load()
    except ValueError as e:
        if "file type is not supported in partition" in str(e):
            # Convert the file to .txt and try again
            txt_file = convert_to_txt(gs_file)
            loader = UnstructuredFileLoader(txt_file)
            if split:
                docs = loader.load_and_split()
            else:
                docs = loader.load()
            os.remove(txt_file)  # Remove the temporary .txt file after processing
        else:
            raise e

    for doc in docs:
        doc.metadata["file_sha1"] = file_sha1
        if metadata is not None:
            doc.metadata.update(metadata)

    return docs

def choose_splitter(extension: str, chunk_size: int=1024, chunk_overlap:int=0):
    if extension == ".py":
        return text_splitter.PythonCodeTextSplitter()
    elif extension == ".md":
        return text_splitter.MarkdownTextSplitter()
    
    return text_splitter.RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def chunk_doc_to_docs(documents: list, extension: str = ".md"):
    """Turns a Document object into a list of many Document chunks"""
    for document in documents:
        source_chunks = []
        splitter = choose_splitter(extension)
        for chunk in splitter.split_text(document.page_content):
            source_chunks.append(Document(page_content=chunk, metadata=document.metadata))

        return source_chunks  

def pubsub_to_doc(data: dict, vector_name:str="documents"):
    """Triggered from a message on a Cloud Pub/Sub topic.
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

    if message_data.startswith("gs://"):
        bucket_name, file_name = message_data[5:].split("/", 1)

        # Create a client
        storage_client = storage.Client()

        # Download the file from GCS
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(file_name)

        with tempfile.NamedTemporaryFile() as tmp_file_path:
            blob.download_to_filename(tmp_file_path.name)

            # Load the file into a Document
            doc_path = pathlib.Path(tmp_file_path.name)

        metadata = attributes
        metadata["source"] = file_name
        metadata["type"] = "file_load_gcs"

        docs = read_file_to_document(doc_path, metadata=metadata)
        chunks = chunk_doc_to_docs(docs, doc_path.suffix)

    else:

        hash = compute_sha1_from_content(message_data)
        metadata["file_sha1"] = hash
        metadata["type"] = "message"
        doc = Document(page_content=message_data, metadata=metadata)
        

        chunks = chunk_doc_to_docs([doc], ".txt")

    logging.info("Initiating Supabase store")
    # init embedding and vector store
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    logging.info(f"Supabase URL: {supabase_url}")
    embeddings = OpenAIEmbeddings()
    supabase: Client = create_client(supabase_url, supabase_key)

    vector_store = SupabaseVectorStore(supabase, embeddings, table_name=vector_name)

    logging.info("Adding document to Supabase")
    vector_store.add_documents(chunks)

    logging.info(f"Add doc with metadata: {metadata}")

    return metadata
