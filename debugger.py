#!/Users/mark/dev/ml/langchain/read_github/langchain_github/env/bin/python
# change above to the location of your local Python venv installation

import os
import my_llm.standards as my_llm
import openai
from langchain.chat_models import ChatOpenAI

# Set up OpenAI API
openai.api_key = os.environ["OPENAI_API_KEY"]

chat = ChatOpenAI(temperature=0.4)

memory = my_llm.init_memory("debugger")
memory.clear()

prompt = "List how many ways there are to catch a cat if it has escaped from your house and you need it back inside so you can go to bed"

answer = my_llm.request_llm(prompt, chat, memory)

print(answer)

prompt2 = f"""
Repeat the answer below but in Danish, or if you don't know just say 'munch munch' a lot:
{answer}
"""

answer2 = my_llm.request_llm(prompt2, chat, memory)

memory.save_vectorstore_memory()
