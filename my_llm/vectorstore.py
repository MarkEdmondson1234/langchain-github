import os
import shutil
import atexit
from pathlib import Path

from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter

from langchain.vectorstores import Chroma

from google.api_core.exceptions import NotFound

from google.cloud import storage

class MessageVectorStore:
    """
    Creates a VectorStore and stores messages within it.
        memory_namespace: Governs where vectordata is stored
        messages: Messages sent to this VectorStore
        embedding: The Embedding that is used within this VectorStore e.g. OpenAIEmbeddings()
        bucket_name: if specified saves and loads vectorstore to GCP as well as locally: gs://name-of-bucket
    """
    def __init__(self, memory_namespace, messages, embedding, bucket_name:str=None):
        self.memory_namespace = memory_namespace
        self.vector_db = None
        self.messages = messages
        self.embedding = embedding
        self.bucket_name = bucket_name
        self.bucket_client = None

        if self.bucket_name:
            self._get_set_bucket_client(self.bucket_name)
    
    def set_bucket(self, bucket_name):
        self.bucket_name = bucket_name

        self._get_set_bucket_client(bucket_name)
    
    def get_mem_vectorstore(self):
        """
        Returns the path to the vectorstore directory.
        """
        if not self.memory_namespace:
            print("No memory namespace specified")
            return None

        return Path(os.getenv('MESSAGE_HISTORY',"."), 
                    "vectorstore", self.memory_namespace)


    def clear(self):
        """
        Clears the vectorstore directory.
        """
        dir_path = self.get_mem_vectorstore()

        if dir_path and dir_path.is_dir():
            try:
                shutil.rmtree(dir_path)
                print(f"Directory '{dir_path}' has been deleted.")
            except OSError as e:
                print(f"Error deleting directory '{dir_path}': {e}")
    
    def save_vectorstore_memory(self, documents=None, verbose=False):

        vector_db = self.load_vectorstore_memory()

        source_chunks = self._get_source_chunks(documents)
        ids = vector_db.add_documents(source_chunks)

        if verbose:
            print(f'Saved {len(ids)} documents to vectorstore:')
            for chunk in source_chunks:
                print(chunk.page_content[:30].strip() + "...")
                print(chunk.metadata)

        return ids

    def load_vectorstore_memory(self, embedding=None, verbose=False):

        if self.vector_db is not None:
            return self.vector_db
        
        db_path = self.get_mem_vectorstore()

        if self.bucket_name is not None:
            # Check if the directory exists in the GCS bucket
            directory_path = self._default_gcs_dirname()
            if not self._gcs_directory_exists(self.bucket_name, directory_path):
                print(f"Directory '{directory_path}' not found in the GCS bucket '{self.bucket_name}'")
            else:
                if verbose:
                    print(f"Found directory '{directory_path}' in the GCS bucket '{self.bucket_name}'")

                # now should be available to load locally
                self.get_vectorstore_gcs(self.bucket_name)

        # Check if the Chroma database exists on disk
        if not os.path.exists(db_path):
            # If it doesn't exist, create and persist the database
            vector_db = self.create_vectorstore_memory(embedding=embedding)
        else:
            # If it exists, load the database from disk
            vector_db = self.load_vectorstore_from_disk(embedding=embedding)
            
        self.vector_db = vector_db

        if verbose:
            print("Loaded vectorstore")

        return vector_db

    def load_vectorstore_from_disk(self, embedding):
        db_path = self.get_mem_vectorstore()
        print(f"Loading existing vectorstore database from {db_path}")
        if self.embedding is None and embedding is None:
            print(f"Can't load existing vectorstore database without embedding function e.g. OpenAIEmbeddings()")
            return None
        
        if embedding is not None:
            self.embedding = embedding
        
        return Chroma(persist_directory=str(db_path), embedding_function=self.embedding)

    def _default_gcs_dirname(self):
        local_dir = self.get_mem_vectorstore()
        
        return os.path.dirname(local_dir) + '/' + self.memory_namespace 


    def _gcs_directory_exists(self, bucket_name, prefix):
        """
        Check if a directory exists in a GCS bucket.
        """

        if self.bucket_name is None:
            self.bucket_name = bucket_name

        self._get_set_bucket_client(bucket_name)

        if self.bucket_client:
            for blob in self.bucket_client.list_blobs(prefix=prefix):
                if blob.name.startswith(prefix):
                    return True
        return False
    
    def _get_set_bucket_client(self, bucket_name: str):
        if self.bucket_client is None:
            client = storage.Client()
            try:
                self.bucket_client = client.get_bucket(bucket_name)
            except NotFound:
                print(f"bucket {bucket_name} not found")
                return None
    
    def get_vectorstore_gcs(self, bucket_name, directory_path=None):

        self._get_set_bucket_client(bucket_name)
        
        local_dir = self.get_mem_vectorstore()

        if directory_path is None:
            directory_path = self._default_gcs_dirname()

        if not local_dir:
            print("No local directory specified for vectorstore")
            return

        # Check if the directory exists in the GCS bucket
        if not self._gcs_directory_exists(bucket_name, directory_path):
            print(f"Directory '{directory_path}' not found in the GCS bucket '{bucket_name}'")
            return

        os.makedirs(local_dir, exist_ok=True)
        self._download_directory(self.bucket_client, directory_path, local_dir)

        self.auto_save_vectorstore_gcs(bucket_name, local_dir)

    def _download_directory(self, bucket, prefix, local_dir):
        """
        Download a directory and its contents from GCS bucket to a local directory.
        """
        for blob in bucket.list_blobs(prefix=prefix):
            local_filepath = os.path.join(local_dir, os.path.relpath(blob.name, prefix))
            os.makedirs(os.path.dirname(local_filepath), exist_ok=True)
            with open(local_filepath, "wb") as local_file:
                blob.download_to_file(local_file)

    def _upload_directory(self, bucket, prefix, local_dir):
        """
        Upload a local directory and its contents to a GCS bucket.
        """
        for root, dirs, files in os.walk(local_dir):
            for file in files:
                local_filepath = os.path.join(root, file)
                remote_filepath = os.path.join(prefix, os.path.relpath(local_filepath, local_dir))
                blob = storage.Blob(remote_filepath, bucket)
                with open(local_filepath, "rb") as local_file:
                    blob.upload_from_file(local_file)

    def save_vectorstore_gcs(self, bucket_name, directory_path=None):
        local_dir = self.get_mem_vectorstore()

        if directory_path is None:
            directory_path = self._default_gcs_dirname()

        if not local_dir:
            print("No local directory specified for vectorstore")
            return
        
        self._get_set_bucket_client(bucket_name)

        if self.bucket_client:
            self.upload_directory(self.bucket_client, directory_path, local_dir)

    def auto_save_vectorstore_gcs(self, bucket_name, dir_path):
        print(f"Auto-saving vector store {dir_path} to {bucket_name}")
        atexit.register(self.save_vectorstore_gcs, bucket_name, dir_path)


    def create_vectorstore_memory(self, embedding=None):
        db_path = self.get_mem_vectorstore()

        if embedding is not None:
            self.embedding = embedding

        if self.embedding is None and embedding is None:
            print(f"Can't load existing vectorstore database without embedding function e.g. OpenAIEmbeddings()")
            return None
        
        what_we_are_doing = f'Creating Chroma DB at {db_path} ...'
        print(what_we_are_doing)

        # we need a few messages to init the db
        init_docs = []
        for i in range(5):
            doc = Document(page_content=what_we_are_doing+str(i), metadata={'task': 'chromadb_init'})
            init_docs.append(doc)

        vector_db = Chroma.from_documents(init_docs, 
                                          self.embedding, 
                                          persist_directory=str(db_path))
        self.vector_db = vector_db
        vector_db.persist()

        if self.bucket_name:
            self.auto_save_vectorstore_gcs(self.bucket_name, db_path)

        return vector_db

    def _get_source_chunks(self, documents=None):
        source_chunks = []

        if documents is None:
            documents = self._get_memory_documents()
        # Create a CharacterTextSplitter object for splitting the text
        splitter = CharacterTextSplitter(separator=" ", 
                                         chunk_size=2048, 
                                         chunk_overlap=0)
        for source in documents:
            for chunk in splitter.split_text(source.page_content):
                source_chunks.append(Document(page_content=chunk, 
                                              metadata=source.metadata))

        return source_chunks
    
    def _get_memory_documents(self):
        docs = []
        for message in self.messages:
            doc = Document(page_content=message.content, 
                           metadata={
                               "role": message.role,
                               "timestamp": str(message.timestamp)
                           })
            docs.append(doc)
        return docs
