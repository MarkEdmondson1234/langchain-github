#!/Users/mark/dev/ml/langchain/read_github/langchain_github/env/bin/python
# change above to the location of your local Python venv installation

import os
import my_llm.standards as my_llm
import openai
from langchain.chat_models import ChatOpenAI
from my_llm.langchain_class import PubSubChatMessageHistory

# Set up OpenAI API
openai.api_key = os.environ["OPENAI_API_KEY"]

chat = ChatOpenAI(temperature=0.4)

memory = PubSubChatMessageHistory("debugger")
memory.clear()
# load chat-gpt history
memory.load_chatgpt_export("/Users/mark/dev/ml/chatgpt_export/conversations.json")

summary = memory.apply_summarise_to_memory(n=10)

print("Summary last 10 messages")
print(summary)

memory.save_vectorstore_memory()

answer3 = memory.question_memory("How is a TimedChatMessage defined?")
print(answer3)
