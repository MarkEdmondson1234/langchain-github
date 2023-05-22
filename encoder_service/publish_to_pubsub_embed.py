# imports
import os, shutil, json, re
import pathlib
from langchain.document_loaders.unstructured import UnstructuredFileLoader
from langchain.document_loaders import UnstructuredURLLoader

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
import datetime

load_dotenv()

def contains_url(message_data):
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    if url_pattern.search(message_data):
        return True
    else:
        return False

def extract_urls(text):
    url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    urls = url_pattern.findall(text)
    return urls

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
    now = datetime.datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    day = now.strftime("%d") 
    hour = now.strftime("%H")
    bucket_filepath = f"{vector_name}/{year}/{month}/{day}/{hour}/{os.path.basename(filename)}"

    blob = bucket.blob(bucket_filepath)
    blob.upload_from_filename(filename)

    logging.info(f"File {filename} uploaded to gs://{bucket_name}/{bucket_filepath}")

    return f"gs://{bucket_name}/{bucket_filepath}"


def read_url_to_document(url: str, metadata: dict = None):
    
    loader = UnstructuredURLLoader(urls=[url])
    docs = loader.load()
    if metadata is not None:
        for doc in docs:
            doc.metadata.update(metadata)
    
    logging.info(f"UnstructuredURLLoader docs: {docs}")
    
    return docs


def read_file_to_document(gs_file: pathlib.Path, split=False, metadata: dict = None):
    
    #file_sha1 = compute_sha1_from_file(gs_file.name)
    
    try:
        #TODO: Use UnstructuredAPIFileLoader instead?
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
        #doc.metadata["file_sha1"] = file_sha1
        if metadata is not None:
            doc.metadata.update(metadata)

    return docs

def choose_splitter(extension: str, chunk_size: int=1024, chunk_overlap:int=0):
    if extension == ".py":
        return text_splitter.PythonCodeTextSplitter()
    elif extension == ".md":
        return text_splitter.MarkdownTextSplitter()
    
    return text_splitter.RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

def remove_whitespace(page_content):
    return page_content.replace("\n", " ").replace("\r", " ").replace("\t", " ").replace("  ", " ")


def chunk_doc_to_docs(documents: list, extension: str = ".md"):
    """Turns a Document object into a list of many Document chunks"""
    for document in documents:
        source_chunks = []
        splitter = choose_splitter(extension)
        for chunk in splitter.split_text(remove_whitespace(document.page_content)):
            source_chunks.append(Document(page_content=chunk, metadata=document.metadata))

        return source_chunks  

def data_to_embed_pubsub(data: dict, vector_name:str="documents"):
    """Triggered from a message on a Cloud Pub/Sub topic.
    Args:
         data JSON
    """
    #hash = data['message']['data']
    message_data = base64.b64decode(data['message']['data']).decode('utf-8')
    attributes = data['message'].get('attributes', {})
    messageId = data['message'].get('messageId')
    publishTime = data['message'].get('publishTime')

    logging.info(f"data_to_embed_pubsub was triggered by messageId {messageId} published at {publishTime}")
    logging.info(f"data_to_embed_pubsub data: {message_data}")

    # pubsub from a Google Cloud Storage push topic
    if attributes.get("eventType", None) is not None and attributes.get("payloadFormat", None) is not None:
        eventType = attributes.get("eventType")
        payloadFormat = attributes.get("payloadFormat")
        if eventType == "OBJECT_FINALIZE" and payloadFormat == "JSON_API_V1":
            logging.info("Got valid event from Google Cloud Storage")
            # https://cloud.google.com/storage/docs/json_api/v1/objects#resource-representations
            message_data = 'gs://' + attributes.get("bucketId") + '/' + attributes.get("objectId")
            logging.info(f"Constructed message_data: {message_data}")

    metadata = {}
    chunks = []

    if message_data.startswith('"gs://'):
        message_data = message_data.strip('\"')

    if message_data.startswith("gs://"):
        logging.info("Detected gs://")
        bucket_name, file_name = message_data[5:].split("/", 1)

        # Create a client
        storage_client = storage.Client()

        # Download the file from GCS
        bucket = storage_client.get_bucket(bucket_name)
        blob = bucket.blob(file_name)

        file_name=pathlib.Path(file_name)

        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_file_path = os.path.join(temp_dir, file_name.name)
            blob.download_to_filename(tmp_file_path)

            metadata = {
                "source": message_data,
                "type": "file_load_gcs",
                "bucket_name": bucket_name
            }

            docs = read_file_to_document(tmp_file_path, metadata=metadata)
            chunks = chunk_doc_to_docs(docs, file_name.suffix)

    elif message_data.startswith("http"):
        logging.info(f"Got http message: {message_data}")

        # just in case, extract the URL again
        urls = extract_urls(message_data)

        docs = []
        for url in urls:
            metadata["source"] = url
            metadata["url"] = url
            metadata["type"] = "url_load"
            doc = read_url_to_document(url, metadata=metadata)
            docs.extend(doc)

        chunks = chunk_doc_to_docs(docs)

    else:
        logging.info("No gs:// detected")
        
        the_json = json.loads(message_data)
        metadata = the_json.get("metadata", {})
        the_content = the_json.get("page_content", None)

        if metadata.get("source", None) is not None:
            metadata["source"] = "No source embedded"

        if the_content is None:
            logging.info("No content found")
            return {"metadata": "No content found"}
        
        docs = [Document(page_content=the_content, metadata=metadata)]

        publish_if_urls(the_content, vector_name)

        chunks = chunk_doc_to_docs(docs)
        
    publish_chunks(chunks, vector_name=vector_name)

    logging.info(f"data_to_embed_pubsub published chunks with metadata: {metadata}")

    return metadata

def publish_if_urls(the_content, vector_name):
    """
    Extracts URLs and puts them in a queue for processing on PubSub
    """
    if contains_url(the_content):
        logging.info("Detected http://")

        urls = extract_urls(the_content)
            
        for url in urls:
            publish_text(url, vector_name)


def publish_chunks(chunks: list[Document], vector_name: str):
    logging.info("Publishing chunks to embed_chunk")
    pubsub_manager = PubSubManager(vector_name, pubsub_topic=f"embed_chunk_{vector_name}")
    for chunk in chunks:
        # Convert chunk to string, as Pub/Sub messages must be strings or bytes
        chunk_str = chunk.json()
        pubsub_manager.publish_message(chunk_str)

def publish_text(text:str, vector_name: str):
    logging.info(f"Publishing text to app_to_pubsub_{vector_name}")
    pubsub_manager = PubSubManager(vector_name, pubsub_topic=f"app_to_pubsub_{vector_name}")
    
    pubsub_manager.publish_message(text)