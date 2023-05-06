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

memory = PubSubChatMessageHistory("debugger2")
memory.clear()

# # load chat-gpt history
memory.load_chatgpt_export("/Users/mark/dev/ml/chatgpt_export/conversations.json")

summary = memory.apply_summarise_to_memory(n=10)

# temps = [0.1, 0.25, 0.5, 0.75, 1]
temps = [1]
prompt = f"""
Speculate what could happen next or what were the circumstances leading to the below.  
Prefix your response with 'ELECTRIC SHEEP:'
{summary}
"""
for temp in temps:
    dream = ChatOpenAI(temperature=temp)
    my_llm.request_llm(prompt, dream, memory)


# it searches over the vectorstore, and inserts context into the prompt before sending the answer to LLM
result = memory.question_memory("What messages include ELECTRIC SHEEP?")
print("## Answer: {}".format(result['result']))
print('== Document sources:')
print(result)

