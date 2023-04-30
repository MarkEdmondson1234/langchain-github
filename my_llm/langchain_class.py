from langchain.schema import ChatMessage, BaseChatMessageHistory
from langchain.memory import ConversationTokenBufferMemory
from langchain.llms import OpenAI
from langchain.schema import messages_from_dict, messages_to_dict
import os, json

from datetime import datetime
from dateutil.parser import parse

class TimedChatMessage(ChatMessage):
    timestamp: datetime = None

    def __init__(self, content, role, timestamp=None):
        super().__init__(content=content, role=role, timestamp=timestamp or datetime.utcnow())


class TimedChatMessageHistory(BaseChatMessageHistory):
    memory_namespace: str

    def __init__(self, memory_namespace: str):
        super().__init__()
        self.memory_namespace = memory_namespace
        self.messages = []

    def get_mem_path(self, memory_namespace):
        if os.getenv('MESSAGE_HISTORY'):
            return os.path.join(os.getenv('MESSAGE_HISTORY'), memory_namespace, "memory.json")
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
            mem_path = self.get_mem_path(self.memory_namespace)
            self._write_to_disk(mem_path, timed_message.dict())
        self.messages.append(timed_message)

    def add_ai_message(self, message):
        timed_message = TimedChatMessage(content=message, role="ai")
        if self.memory_namespace:
            mem_path = self.get_mem_path(self.memory_namespace)
            self._write_to_disk(mem_path, timed_message.dict())
        self.messages.append(timed_message)
    
    def clear(self):
        if self.memory_namespace:
            with open(self.get_mem_path(self.memory_namespace), 'w') as f:
                f.write("[]")
        self.messages = []

    def load_chat_history(self):
        if self.memory_namespace:
            filepath = self.get_mem_path(self.memory_namespace)
            if filepath and os.path.isfile(filepath):
                print(f'Loading chat history from {filepath}')
                with open(filepath, 'r') as f:
                    for line in f:
                        message_data = json.loads(line)
                        message_data['timestamp'] = parse(message_data['timestamp'])
                        message_data.pop('additional_kwargs', None)
                        timed_message = TimedChatMessage(**message_data)
                        self.messages.append(timed_message)
            else:
                print("Chat history file does not exist.")
        else:
            print("Memory namespace not set.")
    
    def apply_buffer_to_memory(self, max_token_limit: int =3000):

        short_term_memory = ConversationTokenBufferMemory(
            llm=OpenAI(), 
            max_token_limit=max_token_limit, 
            return_messages=True)

        # Load messages from ChatMessageHistory into ConversationTokenBufferMemory
        for message in self.messages:
            print(message.content)
            if message.role == "user":
                short_term_memory.save_context({"input": message.content}, {"output": ""})
            elif message.role == "ai":
                short_term_memory.save_context({"input": ""}, {"output": message.content})
        
        return short_term_memory

def timed_messages_to_dict(messages):
    dicts = messages_to_dict(messages)
    for message_dict, message in zip(dicts, messages):
        message_dict["timestamp"] = message.timestamp.isoformat()
    return dicts

def timed_messages_from_dict(dicts):
    messages = messages_from_dict(dicts)
    for message_dict, message in zip(dicts, messages):
        message.timestamp = datetime.fromisoformat(message_dict["timestamp"])
    return messages

#history = TimedChatMessageHistory()
#history.add_user_message("hi!")
#history.add_ai_message("whats up?")