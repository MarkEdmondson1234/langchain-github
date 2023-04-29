import openai
import os
import re
import sys

# Add parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from langchain.chains import ConversationChain
from langchain.callbacks import get_openai_callback

from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings

from .langchain_class import TimedChatMessageHistory
from langchain.memory import ConversationTokenBufferMemory
from langchain.llms import OpenAI

# Set up OpenAI API
openai.api_key  = os.environ["OPENAI_API_KEY"]

def apply_buffer_to_memory(chat_history, max_token_limit: int =3000):

    if isinstance(chat_history, ConversationTokenBufferMemory):
        #TODO: but now won't write to disk or have a timestamp - modify TimedChatMessageHistory
        return chat_history

    memory = ConversationTokenBufferMemory(
        llm=OpenAI(), 
        max_token_limit=max_token_limit, 
        return_messages=True)

    # Load messages from ChatMessageHistory into ConversationTokenBufferMemory
    for message in chat_history.messages:
        if message.role == "user":
            memory.save_context({{"input": message.text}}, {{}})
        elif message.role == "ai":
            memory.save_context({{}}, {{"output": message.text}})
    
    return memory

def init_memory(memory_namespace):
    memory = TimedChatMessageHistory(memory_namespace)
    memory.load_chat_history()

    memory = apply_buffer_to_memory(memory)
    
    return memory

def parse_code(code, memory=None):
    text = ""
    if "```" in code:
        match = re.search('(.+?)\`\`\`(python)?\n(.*?)\`\`\`\n(.+?)', code, re.DOTALL)
        if not match:
            print("Couldn't find any code in API response\n", code)
            return None
        code = match.group(3)
        if match and match.group(1) is not None:
            text = match.group(1)
        if match and match.group(4) is not None:
            text = text + match.group(4)
    else:
        if memory:
            memory.chat_memory.add_user_message("You MUST always enclose your code examples with three backticks (```)")
        
    print("==AI FEEDBACK==")
    print(text)
    
    return code + '\n\n"""\n' + text + '"""\n'

totals = {
        "total_tokens": 0,
        "prompt_tokens":0,
        "completion_tokens": 0,
        "successful_requests": 0,
        "total_cost":0.0
    }

def reset_totals():
    _totals = {
            "total_tokens": 0,
            "prompt_tokens":0,
            "completion_tokens": 0,
            "successful_requests": 0,
            "total_cost":0.0
        }
    totals = _totals
    return(totals)

def request_llm(prompt, chat, memory, verbose=False, memory_namespace=None):
    """
    Function to request code generation from the OpenAI API
    """
    print("================================================")
    print(f"==    Requesting LLM {chat.model_name}  ==")
    if verbose: 
        print(prompt)
    
    memory=apply_buffer_to_memory(memory, max_token_limit=3000)
    
    with get_openai_callback() as cb:
        chain = ConversationChain(
            llm=chat,
            verbose=verbose,
            memory=memory)
        output = chain.predict(input=prompt)
        print(cb)
        totals["total_tokens"] += cb.total_tokens
        totals["prompt_tokens"] += cb.prompt_tokens
        totals["completion_tokens"] += cb.completion_tokens
        totals["successful_requests"] += cb.successful_requests
        totals["total_cost"] += cb.total_cost
        print(f"Totals: {totals}")
    
    return output

def request_code(prompt, chat, memory, verbose=False):
    memory.chat_memory.add_user_message("You are an expert AI to help create Python programs. You always enclose your code examples with three backticks (```)")

    output = request_llm(prompt, chat, memory, verbose=verbose)
    code = parse_code(output, memory)

    return(code)


# Save generated code to a file, make the folder if needed
def save_to_file(filename, content, type="w"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, type) as file:
        file.write(content)

def new_vector_db(path, source_chunks, embedding=OpenAIEmbeddings()):
    # Define the path of the repository and Chroma DB
    REPO_PATH = path
    CHROMA_DB_PATH = f'{os.getenv("CHROMA_DB_PATH", default = "./chroma")}/{os.path.basename(REPO_PATH)}'
    print("Chrome DB path: {}".format(CHROMA_DB_PATH))
    
    # Create a new Chroma DB
    print(f'Creating Chroma DB at {CHROMA_DB_PATH} ...')
    vector_db = Chroma.from_documents(source_chunks, embedding, persist_directory=CHROMA_DB_PATH)
    vector_db.persist()

    return vector_db

def load_vector_db(db_path, embedding=OpenAIEmbeddings()):
    # Load an existina Chroma DB
    print(f'Loading Chroma DB from {db_path}.')
    vector_db = Chroma(persist_directory=db_path, embedding_function=embedding)

    return vector_db