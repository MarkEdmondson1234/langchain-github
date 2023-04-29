from langchain.schema import ChatMessage, BaseChatMessageHistory
from langchain.schema import messages_from_dict, messages_to_dict
import os, json

from datetime import datetime

class TimedChatMessage(ChatMessage):
    def __init__(self, message, role, timestamp=None):
        super().__init__(message, role)
        self.timestamp = timestamp or datetime.utcnow()

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

    def add_user_message(self, message):
        timed_message = TimedChatMessage(message, "user")
        if self.memory_namespace:
            with open(self.get_mem_path(self.memory_namespace), 'w') as f:
                json.dump(f, timed_message)
        self.messages.append(timed_message)

    def add_ai_message(self, message):
        timed_message = TimedChatMessage(message, "ai")
        if self.memory_namespace:
            with open(self.get_mem_path(self.memory_namespace), 'w') as f:
                json.dump(f, timed_message)
        self.messages.append(timed_message)
    
    def clear(self):
        if self.memory_namespace:
            with open(self.get_mem_path(self.memory_namespace), 'w') as f:
                f.write("[]")
        self.messages = []

    def load_chat_history(self):
        if self.memory_namespace:
            mem_path = self.get_mem_path(self.memory_namespace)
            if mem_path and os.path.isfile(mem_path):
                print(f'Loading chat history from {mem_path}')
                with open(mem_path, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        message_data = json.loads(line)
                        timed_message = TimedChatMessage(message_data['text'], message_data['sender'])
                        self.messages.append(timed_message)
            else:
                print("Chat history file does not exist.")
        else:
            print("Memory namespace not set.")

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