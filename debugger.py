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

prompt = "How many ways are there to travel between the north pole and Copenhagen directly? Also output a random animal with prefix: ANIMAL:"

answer = my_llm.request_llm(prompt, chat, memory)

print(answer)

prompt2 = f"""
Repeat the answer below but in Danish, or if you don't know just say 'munch munch' a lot:
{answer}
"""

answer2 = my_llm.request_llm(prompt2, chat, memory)

#memory.print_messages()

summary = memory.apply_summarise_to_memory()

print("Summary")
print(summary)

memory.save_vectorstore_memory()

answer3 = memory.question_memory("What random animal have you said?")
print(answer3)