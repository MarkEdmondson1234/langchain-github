import os, json

from langchain.schema import ChatMessage, BaseChatMessageHistory
from langchain.memory import ConversationTokenBufferMemory
from langchain.llms import OpenAI

from langchain.memory import ConversationSummaryBufferMemory

from langchain.chains import ConversationalRetrievalChain

from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings

from datetime import datetime
from dateutil.parser import parse

from google.cloud import pubsub_v1
from google.auth import default
from google.api_core.exceptions import NotFound


class TimedChatMessage(ChatMessage):
    timestamp: datetime = None

    def __init__(self, content, role, timestamp=None):
        super().__init__(content=content, 
                         role=role, 
                         timestamp=timestamp or datetime.utcnow())


class PubSubChatMessageHistory(BaseChatMessageHistory):

    def __init__(self, memory_namespace: str, pubsub_topic: str = None):
        super().__init__()
        self.memory_namespace = memory_namespace
        self.messages = []
        self.mem_path = None

        # Get the project ID from the default Google Cloud settings or the environment variable
        _, project_id = default()
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')

        if self.project_id:
            print(f"Project ID: {self.project_id}")
            # Create the Pub/Sub topic based on the project ID and memory_namespace
            self.pubsub_topic = pubsub_topic or f"projects/{self.project_id}/topics/chat-messages-{memory_namespace}"
            self.publisher = pubsub_v1.PublisherClient()
            self._create_pubsub_topic_if_not_exists()
        else:
            # If no project ID is available, set the pubsub_topic and publisher to None
            print("GOOGLE_CLOUD_PROJECT not set and gcloud default settings not available")
            self.pubsub_topic = None
            self.publisher = None

    def _create_pubsub_topic_if_not_exists(self):
        """Creates the Pub/Sub topic if it doesn't already exist."""
        try:
            # Check if the topic exists
            self.publisher.get_topic(request={"topic": self.pubsub_topic})
        except NotFound:
            # If the topic does not exist, create it
            self.publisher.create_topic(request={"name": self.pubsub_topic})
            print(f"Created Pub/Sub topic: {self.pubsub_topic}")

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

        # Publish to Google Pub/Sub
        if self.publisher and self.pubsub_topic:
            self._publish_to_pubsub(data)

    def _publish_to_pubsub(self, data):
        """Publishes the given data to Google Pub/Sub."""
        message_json = json.dumps(data, default=self._datetime_converter)
        message_bytes = message_json.encode('utf-8')
        future = self.publisher.publish(self.pubsub_topic, message_bytes)
        future.add_done_callback(self._callback)

    @staticmethod
    def _callback(future):
        try:
            message_id = future.result()
            #print(f"Published message with ID: {message_id}")
        except Exception as e:
            print(f"Failed to publish message: {e}")


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
                               llm=OpenAI(),
                               memory_key: str ='history'):

        short_term_memory = ConversationTokenBufferMemory(
            llm=llm, 
            max_token_limit=max_token_limit, 
            memory_key=memory_key,
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

    @staticmethod
    def _get_chat_history(inputs) -> str:
        res = []
        for human, ai in inputs:
            res.append(f"Human:{human}\nAI:{ai}")
        return "\n".join(res)
    
    def question_memory(self, question: str, llm=OpenAI(temperature=0)):
        db = self.load_vectorstore_memory()

        self.add_user_message(question)

        qa_memory = self.apply_buffer_to_memory(llm=llm, memory_key="chat_history")

        qa = ConversationalRetrievalChain.from_llm(
            llm, 
            db.as_retriever(), 
            get_chat_history=self._get_chat_history,
            memory=qa_memory)
        
        result = qa({"question": question})
        answer = result["answer"]
        self.add_ai_message(answer)

        return answer
    
    def save_vectorstore_memory(self, embedding=OpenAIEmbeddings()):
        db_path = self.get_mem_vectorstore()
        print(f'Saving Chroma DB at {db_path} ...')
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



