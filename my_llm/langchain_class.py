import os, json

from langchain.schema import BaseChatMessageHistory
from langchain.memory import ConversationTokenBufferMemory
from langchain.llms import OpenAI

from langchain.memory import ConversationSummaryBufferMemory

from langchain.chains import RetrievalQA

from langchain import PromptTemplate

from langchain.docstore.document import Document
from langchain.embeddings.openai import OpenAIEmbeddings

from datetime import datetime
from dateutil.parser import parse

from my_llm.pubsub_manager import PubSubManager
from my_llm.vectorstore import MessageVectorStore
from my_llm.timed_chat_message import TimedChatMessage

import logging

logging.basicConfig(level=logging.INFO)

class PubSubChatMessageHistory(BaseChatMessageHistory):

    def __init__(self, 
                 memory_namespace: str, 
                 pubsub_topic: str = None, 
                 bucket_name: str = None,
                 embedding = None):
        super().__init__()
        self.memory_namespace = memory_namespace
        self.messages = []
        self.mem_path = None
        self.pubsub_manager = PubSubManager(memory_namespace, pubsub_topic=pubsub_topic)
        self.embedding = embedding if embedding is not None else OpenAIEmbeddings()
        self.vectorstore_manager = MessageVectorStore(
            memory_namespace, 
            messages = self.messages, 
            embedding=OpenAIEmbeddings(),
            bucket_name=bucket_name)
    
    def set_bucket(self, bucket_name):
        if self.vectorstore_manager:
            self.vectorstore_manager.set_bucket(bucket_name)

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

    @staticmethod
    def _datetime_converter(o):
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError("Object of type datetime is not JSON serializable")
    
    def _write_to_disk(self, data, verbose:bool =False):
        filepath = self.get_mem_path()
        if not filepath:
            return None
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        data = data.dict()

        # Append the new data as a JSON line
        if verbose:
            print(f"Writing to {filepath} with data")
        with open(filepath, 'a') as f:
            json.dump(data, f, default=self._datetime_converter)
            f.write('\n')

    def _route_message(self, timed_message, verbose: bool=False):

        logging.debug('_route_message')
        metadata = timed_message.metadata if timed_message.metadata is not None else {}
        metadata["role"] = timed_message.role
        metadata["timestamp"] = str(timed_message.timestamp)
        metadata["embedding"] = self.embedding.embed_query(timed_message.content) if self.embedding is not None else ""
        doc = Document(page_content=timed_message.content, metadata=metadata)

        # write to disk
        if self.memory_namespace:
            logging.debug("_route_message: write to disk")
            self._write_to_disk(timed_message, verbose=verbose)
        
        # Publish to Google Pub/Sub
        if self.pubsub_manager:
            logging.debug("_route_message: pubsub")
            self.pubsub_manager.publish_message(timed_message, verbose=verbose)

        # save to vectorstore
        if self.vectorstore_manager:
            logging.debug("_route_message: vectorstore")
            metadata.pop("embedding")
            doc = Document(page_content=timed_message.content, metadata=metadata)
            self.save_vectorstore_memory([doc], verbose=verbose)
            self.vectorstore_manager.messages.append(timed_message)
    

    def save_vectorstore_memory(self, docs, verbose=False):
        if not self.vectorstore_manager:
            print("No vectorstore found to save to")
            return
        logging.debug("Calling vectorstore_manager.save_vectorstore_memory")
        self.vectorstore_manager.save_vectorstore_memory(docs, verbose=verbose)

    def load_vectorstore_memory(self, verbose=False):
        if not self.vectorstore_manager:
            print("No vectorstore found to load")
            return

        return self.vectorstore_manager.load_vectorstore_memory(verbose=verbose)

    def add_user_message(self, message, metadata: dict=None, verbose=False):
        timed_message = TimedChatMessage(content=message, role="user", metadata=metadata)
        self._route_message(timed_message, verbose=verbose)

        self.messages.append(timed_message)

    def add_ai_message(self, message, metadata: dict=None, verbose=False):
        timed_message = TimedChatMessage(content=message, role="ai", metadata=metadata)
        self._route_message(timed_message, verbose=verbose)

        self.messages.append(timed_message)

    def add_system_message(self, message, metadata:dict=None, verbose=False):
        timed_message = TimedChatMessage(content=message, role="system", metadata=metadata)
        self._route_message(timed_message, verbose=verbose)

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
        if self.vectorstore_manager:
            self.vectorstore_manager.clear()

    
    def print_messages(self, n: int =None):
        if not self.messages:
            print("No messages found")
            return None
        
        if n is None:
            n = 10000
        
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

    def _chat_history_prompt(self):
        # create prompt to pass in to LLM
        template = """
Here is the chat history for this conversation between you (labelled AI) and me (labelled Human)\n
{chat_history}
"""

        return PromptTemplate(
            input_variables=["chat_history"],
            template=template,
        )
    
    def question_memory(self, question: str, 
                        llm=OpenAI(temperature=0), 
                        verbose=False,
                        chat_history=None):
        
        db = self.vectorstore_manager.load_vectorstore_memory()
        docs = db.similarity_search(question)
        if len(docs) == 0:
            logging.info(f"No documents found similar to your question: {question}")

        history = None
        if chat_history:
            prompt = self._chat_history_prompt()
            history = self._get_chat_history(chat_history)
            question = prompt.format(chat_history=history) + f'\n{question}'

        if verbose:
            print(f"Question: {question}")
        logging.info(f"Prompt after processing: {question}")

        # Load a QA chain
        # TODO: Use ConversationalRetrievalChain
        qa = RetrievalQA.from_chain_type(
            llm=llm, 
            chain_type="stuff",
            retriever=db.as_retriever(), 
            return_source_documents=True)
        
        result = qa({"query": question})
        answer = result["result"]
        metadata={"task": "QnA"}

        if result.get('source_documents') is not None:
            source_metadata = []
            for doc in result.get('source_documents'):
                # if this isn't done we get a recursive big blob for 'sources'
                filtered_metadata = {key: value for key, value in doc.metadata.items() if key != 'sources'}
                p = {"page_content": doc.page_content, 
                     "page_metadata": filtered_metadata}
                source_metadata.append(p)

            metadata = {"task": "QnA", "sources":json.dumps(source_metadata)}
            if history:
                metadata["history"] = history

        self.add_user_message(question, metadata={"task": "QnA"}, verbose=verbose)
        self.add_ai_message(answer, metadata=metadata, verbose=verbose)

        return result
    
    
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

    



