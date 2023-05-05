import os, json, shutil

from langchain.schema import ChatMessage, BaseChatMessageHistory
from langchain.memory import ConversationTokenBufferMemory
from langchain.llms import OpenAI

from langchain.memory import ConversationSummaryBufferMemory

from langchain.chains import RetrievalQA

from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings

from datetime import datetime
from dateutil.parser import parse

from google.cloud import pubsub_v1
from google.auth import default
from google.api_core.exceptions import NotFound

from pydantic import Field

class TimedChatMessage(ChatMessage):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)

    def __init__(self, content, role, timestamp=None, metadata=None, **kwargs):
        kwargs['timestamp'] = timestamp or datetime.utcnow()
        kwargs['metadata'] = metadata if metadata is not None else {}
        super().__init__(content=content, role=role, **kwargs)


class PubSubChatMessageHistory(BaseChatMessageHistory):

    def __init__(self, memory_namespace: str, pubsub_topic: str = None):
        super().__init__()
        self.memory_namespace = memory_namespace
        self.messages = []
        self.mem_path = None
        self.vector_db = None

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

    def _publish_to_pubsub(self, data):
        """Publishes the given data to Google Pub/Sub."""
        message_json = json.dumps(data, default=self._datetime_converter)
        message_bytes = message_json.encode('utf-8')
        attr = {"namespace": self.memory_namespace}
        future = self.publisher.publish(self.pubsub_topic, message_bytes, attrs=json.dumps(attr))
        future.add_done_callback(self._callback)

    @staticmethod
    def _callback(future):
        try:
            message_id = future.result()
            #print(f"Published message with ID: {message_id}")
        except Exception as e:
            print(f"Failed to publish message: {e}")

    def _route_message(self, timed_message):
        # write to disk
        if self.memory_namespace:
            mem_path = self.get_mem_path()
            if mem_path:
                self._write_to_disk(mem_path, timed_message.dict())
        
        # Publish to Google Pub/Sub
        if self.publisher and self.pubsub_topic:
            self._publish_to_pubsub(timed_message.dict())
        
        # save to vectorstore
        metadata = timed_message.metadata if timed_message.metadata is not None else {}
        metadata["role"] = timed_message.role
        metadata["timestamp"] = str(timed_message.timestamp)
        doc = Document(page_content=timed_message.content, metadata=metadata)

        self.save_vectorstore_memory([doc])


    def add_user_message(self, message, metadata: dict=None):
        timed_message = TimedChatMessage(content=message, role="user", metadata=metadata)
        self._route_message(timed_message)

        self.messages.append(timed_message)

    def add_ai_message(self, message, metadata: dict=None):
        timed_message = TimedChatMessage(content=message, role="ai", metadata=metadata)
        self._route_message(timed_message)

        self.messages.append(timed_message)

    def add_system_message(self, message, metadata:dict=None):
        timed_message = TimedChatMessage(content=message, role="system", metadata=metadata)
        self._route_message(timed_message)

        self.messages.append(timed_message)
    
    def clear(self):
        if self.memory_namespace:
            mem_path = self.get_mem_path()
            if mem_path and os.path.isfile(mem_path):
                with open(self.get_mem_path(), 'w') as f:
                    f.write("\n")
                print("Cleared memory")
        self.messages = []
        
        # remove any vectorstore
        dir_path = self.get_mem_vectorstore()

        # Check if the Chroma database exists on disk
        if os.path.isdir(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"Directory '{dir_path}' has been deleted.")
            except OSError as e:
                print(f"Error deleting directory '{dir_path}': {e}")
    
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
                expected_keys = {'timestamp', 'user', 'message'}  # Add expected keys here
                metadata = {k: v for k, v in message_data.items() if k not in expected_keys}
                if metadata:
                    message_data['metadata'] = metadata

                # Remove unexpected keys from message_data before passing to TimedChatMessage
                for key in metadata:
                    message_data.pop(key, None)

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
                               n = None,
                               max_token_limit: int =3000,
                               llm=OpenAI(),
                               memory_key: str ='history'):

        short_term_memory = ConversationTokenBufferMemory(
            llm=llm, 
            max_token_limit=max_token_limit, 
            memory_key=memory_key,
            return_messages=True)

        # Load messages from TimedChatMessageHistory into ConversationTokenBufferMemory
        short_term_memory = self._switch_memory(short_term_memory, n = n)

        return short_term_memory
    
    def apply_summarise_to_memory(self, 
                                  n = None,
                                  max_token_limit: int =3000,
                                  llm=OpenAI()):

        summary_memory = ConversationSummaryBufferMemory(
            llm=llm, 
            max_token_limit=max_token_limit)
        
        summary_memory = self._switch_memory(summary_memory, n=n)
        
        messages = summary_memory.chat_memory.messages
        
        summary = summary_memory.predict_new_summary(messages, "")

        self.add_ai_message(summary, metadata={"task": "summary"})

        return summary
    
    def _switch_memory(self, memory, n = None):
        i = 0
        for message in self.messages:
            if n and i >= n:
                break
            i += 1
            #print(message.content)
            if message.role == "user":
                memory.save_context({"input": message.content}, 
                                    {"output": ""})
            elif message.role == "ai":
                memory.save_context({"input": ""}, 
                                    {"output": message.content})
        
        return memory
    


    @staticmethod
    def _get_chat_history(inputs) -> str:
        res = []
        for human, ai in inputs:
            res.append(f"Human:{human}\nAI:{ai}")
        return "\n".join(res)
    
    def question_memory(self, question: str, llm=OpenAI(temperature=0)):
        db = self.load_vectorstore_memory()

        docs = db.similarity_search(question)
        if len(docs) == 0:
            print("No documents found similar to your question")
            return None

        # Load a QA chain
        qa = RetrievalQA.from_chain_type(
            llm=llm, 
            chain_type="stuff",
            retriever=db.as_retriever(), 
            return_source_documents=True)
        
        self.add_user_message(question, metadata={"task": "QnA"})
        
        result = qa({"query": question})
        answer = result["result"]
        metadata={"task": "QnA"}

        if result.get('source_documents') is not None:
            source_metadata = []
            for doc in result.get('source_documents'):
                p = {"page_content": doc.page_content, 
                     "page_metadata": doc.metadata}
                source_metadata.append(p)

            metadata = {"task": "QnA", "sources":json.dumps(source_metadata)}

        self.add_ai_message(answer, metadata=metadata)

        return result
    
    def create_vectorstore_memory(self, embedding=OpenAIEmbeddings()):
        db_path = self.get_mem_vectorstore()
        print(f'Creating Chroma DB at {db_path} ...')
        source_chunks = self._get_source_chunks()
        vector_db = Chroma.from_documents(source_chunks, 
                                          embedding, 
                                          persist_directory=db_path)
        self.vector_db = vector_db
        vector_db.persist()

        return vector_db
    
    def save_vectorstore_memory(self, documents=None):

        if self.vector_db is None:
            vector_db = self.load_vectorstore_memory()
        else:
            vector_db = self.vector_db

        source_chunks = self._get_source_chunks(documents)
        ids = vector_db.add_documents(source_chunks)

        print(f'Saved documents to vector store')

        return ids

    def load_vectorstore_memory(self, embedding=OpenAIEmbeddings()):
        db_path = self.get_mem_vectorstore()

        # Check if the Chroma database exists on disk
        if not os.path.exists(db_path):
            # If it doesn't exist, create and persist the database
            vector_db = self.create_vectorstore_memory()
        else:
            # If it exists, load the database from disk
            print(f"Loading existing vectorstore database from {db_path}")
            vector_db = Chroma(persist_directory=db_path, embedding_function=embedding)

        self.vector_db = vector_db

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
    
    
    def load_chatgpt_export(self, conversations_file: str):
        if not os.path.isfile(conversations_file):
            raise Exception(f"Could not find a file to load from {conversations_file}")

        with open(conversations_file, "r") as f:
            json_str = f.read()
        
        chatgpt_messages = self._process_chatgpt_json(json_str)
        
        print(f"Loaded {conversations_file} into messages")

        return chatgpt_messages

    def _process_chatgpt_json(self, json_str: str):
        data = json.loads(json_str)
        messages_data = []
        for line in data:
            message_data = [item["message"] for item in line["mapping"].values() if item["message"] is not None]
            messages_data.append(message_data)
        
        timed_messages = []
        for message_data in messages_data:
            for message in message_data:
                content = message["content"]["parts"][0]
                role = message["author"]["role"]
                timestamp = datetime.fromtimestamp(message["create_time"])
                
                timed_message = TimedChatMessage(content=content, 
                                                 role=role, 
                                                 timestamp=timestamp, 
                                                 metadata={"task": "ChatGPT"})
                timed_messages.append(timed_message)
                # write to disk
                if self.memory_namespace:
                    mem_path = self.get_mem_path()
                    if mem_path:
                        self._write_to_disk(mem_path, timed_message.dict())
                # Publish to Google Pub/Sub
                if self.publisher and self.pubsub_topic:
                    self._publish_to_pubsub(timed_message.dict())

                self.messages.append(timed_message)
        
        return timed_messages

    



