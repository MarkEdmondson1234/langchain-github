# imports
import os, shutil, json
import pathlib
from langchain.document_loaders.unstructured import UnstructuredFileLoader
from langchain.docstore.document import Document
from google.cloud import storage
import base64
import langchain.text_splitter as text_splitter

from dotenv import load_dotenv
import tempfile
import hashlib
from langchain.schema import Document
import logging
from my_llm.pubsub_manager import PubSubManager

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

def add_file_to_gcs(filename: str, vector_name="qa_documents", bucket_name: str=None):

    storage_client = storage.Client()

    bucket_name = bucket_name if bucket_name is not None else os.getenv('GCS_BUCKET', None)
    if bucket_name is None:
        raise ValueError("No bucket found to upload to: GCS_BUCKET returned None")
    

    bucket = storage_client.get_bucket(bucket_name)
    bucket_filepath = f"{vector_name}/{os.path.basename(filename)}"

    blob = bucket.blob(bucket_filepath)
    blob.upload_from_filename(filename)

    print(f"File {filename} uploaded to gs://{bucket_name}/{bucket_filepath}")

    return f"gs://{bucket_name}/{bucket_filepath}"


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

def data_to_embed_pubsub(data: dict, vector_name:str="documents"):
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
    metadata["message_id"] = messageId
    metadata["publish_time"] = publishTime

    chunks = []

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

    publish_chunks(chunks, vector_name=vector_name)

    logging.info(f"Published chunks with metadata: {metadata}")

    return metadata

def publish_chunks(chunks, vector_name: str):
    logging.info("Initiating Pubsub client")
    pubsub_manager = PubSubManager(vector_name, pubsub_topic="embed_chunk")
    for chunk in chunks:
        # Convert chunk to string, as Pub/Sub messages must be strings or bytes
        chunk_str = chunk.json()
        pubsub_manager.publish_message(chunk_str)

def publish_text(text, vector_name: str, metadata = {}):
    chunks = [Document(page_content=text, metadata=metadata)]
    publish_chunks(chunks, vector_name)