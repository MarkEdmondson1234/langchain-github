import os, json

from langchain.schema import ChatMessage, BaseChatMessageHistory
from langchain.memory import ConversationTokenBufferMemory
from langchain.llms import OpenAI

from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings

from datetime import datetime
from dateutil.parser import parse

class TimedChatMessage(ChatMessage):
    timestamp: datetime = None

    def __init__(self, content, role, timestamp=None):
        super().__init__(content=content, 
                         role=role, 
                         timestamp=timestamp or datetime.utcnow())


class TimedChatMessageHistory(BaseChatMessageHistory):
    memory_namespace: str

    def __init__(self, memory_namespace: str):
        super().__init__()
        self.memory_namespace = memory_namespace
        self.messages = []

    def get_mem_path(self):
        if not self.memory_namespace:
            print("No memory namespace specified")
            return None

        if os.getenv('MESSAGE_HISTORY'):
            return os.path.join(os.getenv('MESSAGE_HISTORY'), 
                                self.memory_namespace, 
                                "memory.json")
        else:
            print('Found no MESSAGE_HISTORY set')
            return None
        
    def get_mem_vectorstore(self):
        if not self.memory_namespace:
            print("No memory namespace specified")
            return None
        
        if os.getenv('MESSAGE_HISTORY'):
            return os.path.join(os.getenv('MESSAGE_HISTORY'), 
                                self.memory_namespace, 
                                "chroma/")
        else:
            print('Found no MESSAGE_HISTORY set')
            return None
        
    def _datetime_converter(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError("Object of type datetime is not JSON serializable")
    
    def _write_to_disk(self, filepath, data):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Append the new data as a JSON line
        with open(filepath, 'a') as f:
            json.dump(data, f, default=self._datetime_converter)
            f.write('\n')

    def add_user_message(self, message):
        timed_message = TimedChatMessage(content=message, role="user")
        if self.memory_namespace:
            mem_path = self.get_mem_path()
            if mem_path:
                self._write_to_disk(mem_path, timed_message.dict())
        self.messages.append(timed_message)

    def add_ai_message(self, message):
        timed_message = TimedChatMessage(content=message, role="ai")
        if self.memory_namespace:
            mem_path = self.get_mem_path()
            if mem_path:
                self._write_to_disk(mem_path, timed_message.dict())
        self.messages.append(timed_message)
    
    def clear(self):
        if self.memory_namespace:
            mem_path = self.get_mem_path()
            if mem_path and os.path.isfile(mem_path):
                with open(self.get_mem_path(), 'w') as f:
                    f.write("{}\n")
                print("Cleared memory")
        self.messages = []
    
    def print_messages(self):
        for message in self.messages:
            print(message)

    def load_chat_history(self):
        if self.memory_namespace:
            mem_path = self.get_mem_path()
            if mem_path and os.path.isfile(mem_path):
                print(f'Loading chat history from {mem_path}')
                with open(mem_path, 'r') as f:
                    for line in f:
                        message_data = json.loads(line)
                        message_data['timestamp'] = parse(message_data['timestamp'])
                        message_data.pop('additional_kwargs', None)
                        timed_message = TimedChatMessage(**message_data)
                        self.messages.append(timed_message)
                print('Loaded')
            else:
                print("Chat history file does not exist.")
        else:
            print("Memory namespace not set.")
    
    def apply_buffer_to_memory(self, max_token_limit: int =3000):

        short_term_memory = ConversationTokenBufferMemory(
            llm=OpenAI(), 
            max_token_limit=max_token_limit, 
            return_messages=True)

        # Load messages from TimedChatMessageHistory into ConversationTokenBufferMemory
        for message in self.messages:
            print(message.content)
            if message.role == "user":
                short_term_memory.save_context({"input": message.content}, {"output": ""})
            elif message.role == "ai":
                short_term_memory.save_context({"input": ""}, {"output": message.content})
        
        return short_term_memory
    
    def save_vectorstore_memory(self):
        db_path = self.get_mem_vectorstore()
        print(f'Creating Chroma DB at {db_path} ...')
        source_chunks = self._get_source_chunks()
        vector_db = Chroma.from_documents(source_chunks, 
                                          OpenAIEmbeddings(), 
                                          persist_directory=db_path)
        vector_db.persist()

        return vector_db

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

    def _get_source_chunks(self):
        source_chunks = []

        # Create a CharacterTextSplitter object for splitting the text
        splitter = CharacterTextSplitter(separator=" ", chunk_size=1024, chunk_overlap=0)
        for source in self._get_memory_documents():
            for chunk in splitter.split_text(source.page_content):
                source_chunks.append(Document(page_content=chunk, metadata=source.metadata))

        return source_chunks

