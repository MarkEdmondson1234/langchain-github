import os
import shutil
from pathlib import Path

from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter

from langchain.vectorstores import Chroma

from my_llm.timed_chat_message import TimedChatMessage

class MessageVectorStore:
    """
    Creates a VectorStore and stores messages within it
    """
    def __init__(self, memory_namespace, messages, embedding):
        self.memory_namespace = memory_namespace
        self.vector_db = None
        self.messages = messages
        self.embedding = embedding
    
    def get_mem_vectorstore(self):
        """
        Returns the path to the vectorstore directory.
        """
        if not self.memory_namespace:
            print("No memory namespace specified")
            return None

        if os.getenv('MESSAGE_HISTORY'):
            return Path(os.getenv('MESSAGE_HISTORY'), self.memory_namespace, "chroma")
        else:
            print('Found no MESSAGE_HISTORY set')
            return None

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

    def load_vectorstore_memory(self, embedding=None):

        if self.vector_db is not None:
            return self.vector_db
        
        db_path = self.get_mem_vectorstore()

        # Check if the Chroma database exists on disk
        if not os.path.exists(db_path):
            # If it doesn't exist, create and persist the database
            vector_db = self.create_vectorstore_memory(embedding=embedding)
        else:
            # If it exists, load the database from disk
            print(f"Loading existing vectorstore database from {db_path}")
            if self.embedding is None and embedding is None:
                print(f"Can't load existing vectorstore database without embedding function e.g. OpenAIEmbeddings()")
                return None
            
            if embedding is not None:
                self.embedding = embedding
            
            vector_db = Chroma(persist_directory=str(db_path), embedding_function=self.embedding)
 
        self.vector_db = vector_db

        return vector_db

    def create_vectorstore_memory(self, embedding=None):
        db_path = self.get_mem_vectorstore()

        if self.embedding is None and embedding is None:
            print(f"Can't load existing vectorstore database without embedding function e.g. OpenAIEmbeddings()")
            return None
        
        what_we_are_doing = f'Creating Chroma DB at {db_path} ...'
        print(what_we_are_doing)

        # we need a message to init the db
        init_message = TimedChatMessage(content=what_we_are_doing, 
                                        role="system", 
                                        metadata={'task': 'chromadb_init'})

        source_chunks = self._get_source_chunks(init_message)
        vector_db = Chroma.from_documents(source_chunks, 
                                          embedding, 
                                          persist_directory=db_path)
        self.vector_db = vector_db
        vector_db.persist()

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
