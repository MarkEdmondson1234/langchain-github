import os, json

from langchain.schema import ChatMessage, BaseChatMessageHistory
from langchain.memory import ConversationTokenBufferMemory
from langchain.llms import OpenAI

from langchain.memory import ConversationSummaryBufferMemory


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
        self.mem_path = None
    
    def set_mem_path(self, path: str):
        self.mem_path = path


    def get_mem_path(self):
        if self.mem_path:
            return self.mem_path
        
        if not self.memory_namespace:
            print("No memory namespace specified")
            return None

        if os.getenv('MESSAGE_HISTORY'):
            self.mem_path = os.path.join(os.getenv('MESSAGE_HISTORY'), 
                                self.memory_namespace, 
                                "memory.json")
            return self.mem_path
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

    @staticmethod
    def _datetime_converter(o):
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError("Object of type datetime is not JSON serializable")
    
    def _write_to_disk(self, filepath: str, data):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Append the new data as a JSON line
        #print(f"Data to be written: {data}")
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
                    f.write("\n")
                print("Cleared memory")
        self.messages = []
    
    def print_messages(self, n: int =None):
        if not self.messages:
            print("No messages found")
            return None
        
        i = 0
        for message in self.messages:
            if n and n<=i: 
                break
            i += 1
            print(message)

    def _load_newline_json(self, mem_path, n):
        with open(mem_path, 'r') as f:
            i = 0
            for line in f:
                line = line.strip()  # Remove any leading/trailing whitespace
                if line:  # Only process non-empty lines
                    if n and n<=i:
                        break
                    i += 1
                    message_data = json.loads(line)
                    message_data['timestamp'] = parse(message_data['timestamp'])
                    message_data.pop('additional_kwargs', None)
                    timed_message = TimedChatMessage(**message_data)
                    self.messages.append(timed_message)
        print('Loaded')

    def load_chat_history(self, n: int =None):
        if self.memory_namespace:
            mem_path = self.get_mem_path()
            if mem_path and os.path.isfile(mem_path):
                print(f'Loading chat history from {mem_path}')
                self._load_newline_json(mem_path, n)
            else:
                print("Chat history file does not exist.")
        else:
            print("Memory namespace not set.")
    
    def apply_buffer_to_memory(self, 
                               max_token_limit: int =3000,
                               llm=OpenAI()):

        short_term_memory = ConversationTokenBufferMemory(
            llm=llm, 
            max_token_limit=max_token_limit, 
            return_messages=True)

        # Load messages from TimedChatMessageHistory into ConversationTokenBufferMemory
        short_term_memory = self._switch_memory(short_term_memory)

        return short_term_memory
    
    def apply_summarise_to_memory(self, 
                                  max_token_limit: int =3000,
                                  llm=OpenAI()):

        summary_memory = ConversationSummaryBufferMemory(
            llm=llm, 
            max_token_limit=max_token_limit)
        
        summary_memory = self._switch_memory(summary_memory)
        
        messages = summary_memory.chat_memory.messages
        summary = summary_memory.predict_new_summary(messages, "")
        self.add_ai_message(summary)

        return summary
    
    def _switch_memory(self, memory):
        for message in self.messages:
            #print(message.content)
            if message.role == "user":
                memory.save_context({"input": message.content}, 
                                    {"output": ""})
            elif message.role == "ai":
                memory.save_context({"input": ""}, 
                                    {"output": message.content})
        
        return memory
    
    def load_vectorstore_memory(self, embedding=OpenAIEmbeddings()):
        db_path = self.get_mem_vectorstore()

        print(f'Loading Chroma DB from {db_path}.')
        vector_db = Chroma(persist_directory=db_path, 
                           embedding_function=embedding)

        return vector_db
    
    def save_vectorstore_memory(self, embedding=OpenAIEmbeddings()):
        db_path = self.get_mem_vectorstore()
        print(f'Creating Chroma DB at {db_path} ...')
        source_chunks = self._get_source_chunks()
        vector_db = Chroma.from_documents(source_chunks, 
                                          embedding, 
                                          persist_directory=db_path)
        vector_db.persist()

        return vector_db

    def _get_source_chunks(self):
        source_chunks = []

        # Create a CharacterTextSplitter object for splitting the text
        splitter = CharacterTextSplitter(separator=" ", 
                                         chunk_size=1024, 
                                         chunk_overlap=0)
        for source in self._get_memory_documents():
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



