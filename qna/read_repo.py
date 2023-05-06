#!/Users/mark/dev/ml/langchain/read_github/langchain_github/env/bin/python
# change above to the location of your local Python venv installation
import sys, os

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

import pathlib
import argparse
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain.text_splitter import PythonCodeTextSplitter
from langchain.chat_models import ChatOpenAI
from my_llm import standards as my_llm
from my_llm.langchain_class import PubSubChatMessageHistory
from langchain import PromptTemplate

parser = argparse.ArgumentParser(description="Chat with a GitHub repository",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("repo", help="The GitHub repository on local disk")
parser.add_argument("--reindex", action="store_true", help="Whether to re-index the doc database that supply context to the Q&A")
parser.add_argument("--ext", help="Comma separated list of file extensions to include. Defaults to '.md,.py'")
parser.add_argument("--ignore", help="Directory to ignore file imports from. Defaults to 'env/'")
parser.add_argument("--resummarise", action="store_true", help="Recreate the code.md files describing the code")
args = parser.parse_args()
config = vars(args)

chat = ChatOpenAI(temperature=0.4)

# Get Markdown documents from a repository
def get_repo_docs(repo_path, extension, memory):
    repo = pathlib.Path(repo_path)
    
    ignore = 'env/'
    if config['ignore']:
        ignore = config['ignore']  

    ignore_path = repo / ignore
    if not ignore_path.is_dir():
        print("WARNING: --ignore must be a directory")
    
    print('Ignoring %s' % ignore_path)
    
    exts = extension.split(",")
    for ext in exts:
        # Generate summary md files
        if ext!=".md":
            for non_md_file in repo.glob(f"**/*{ext}"):
                if str(non_md_file).startswith(str(ignore_path)):
                      continue
                generate_code_summary(non_md_file, memory)
                              
		# Iterate over all files in the repo (including subdirectories)
        print(f"Reading {ext} files")
        i = 0
        j = 0
        for md_file in repo.glob(f"**/*{ext}"):

            if str(md_file).startswith(str(ignore_path)):
                j += 1
                continue
            
            i += 1
			# Read the content of the file
            try:
                with open (md_file, "r") as file:
                    rel_path = md_file.relative_to(repo)
                    yield Document(page_content=file.read(), metadata={"source": str(rel_path)})
            except Exception as e:
                print(f"Error reading {md_file}: " + str(e))
        
        print(f"Read {i} and ignored {j} {ext} files.")
        
    print("Read all files")

# Function to summarise code from the OpenAI API     
def generate_code_summary(a_file, memory):
    
    new_file_name = a_file.with_suffix('.md')
    if os.path.isfile(new_file_name) and not config['resummarise']:
         #print(f"Skipping generating summary as found existing code summary file: {new_file_name}")
         return
    
    print("================================================")
    print(f"Requesting code summary for {a_file}   ")
    print("================================================")

    with open(a_file, "r") as file:
        code = file.read()
    
    if len(code) < 10:
        #print(f"Skipping generation as not enough information.  Got: {code}")
        return

    source_chunks = []
    splitter = PythonCodeTextSplitter()
    for chunk in splitter.split_text(code):
        source_chunks.append(Document(page_content=chunk, metadata={"source": a_file}))    

    # create prompt to pass in to LLM
    template = """
Summarise what the code does below.  Use Markdown in your output. 
Use this template:
# heading
summary of script purpose
## functions
How the functions relate to each other

# Inputs and outputs for each function
Description of each function's inputs and outputs

The code to summarise is below:
{code}
"""

    prompt = PromptTemplate(
        input_variables=["code"],
        template=template,
    )
    
    new_file_name = a_file.with_suffix('.md')

    for chunk in source_chunks:
        summary = my_llm.request_llm(
            prompt.format(code=chunk.page_content), 
            chat, 
            memory)
    
        result = my_llm.parse_code(summary, memory)
        if result is not None:
            response = result
        else:
            print("Got no code to parse")
            response = summary
    
        my_llm.save_to_file(new_file_name, response + '\n\n', type = "a")
    
    return
    
# Get source chunks from a repository
def get_source_docs(repo_path, extension, memory):
    source_chunks = []

    splitter = CharacterTextSplitter(separator=" ", chunk_size=1024, chunk_overlap=0)
    for source in get_repo_docs(repo_path, extension, memory):
        if extension == ".py":
            splitter = PythonCodeTextSplitter()
        for chunk in splitter.split_text(source.page_content):
            source_chunks.append(Document(page_content=chunk, metadata=source.metadata))

    return source_chunks

def main():

    # Define the path of the repository and Chroma DB
    REPO_PATH =config['repo']

    memory = PubSubChatMessageHistory("qna_documents")

    if config['reindex']:
		# Create a new Chroma DB
        exts = '.md,.py'
        if config['ext']:
            exts = config['ext']
        source_chunks = get_source_docs(REPO_PATH, exts, memory=memory)
        memory.save_vectorstore_memory(source_chunks)
	
    while True:
        print('\n\033[31m' + 'Ask a question. CTRL + C to quit.')
        print ("If I don't know, feel free to tell me so I can learn and answer more accurately next time with your reply"  + '\033[m')
        user_input = input()
        print('\033[31m')
        answer = memory.question_memory(user_input, llm=chat)
        if answer is not None:
            if answer.get('source_documents') is not None:
                print('\n== Document sources:')
                i = 0
                for doc in answer.get('source_documents'):
                    i += 1
                    print(f'-- Source {i}')
                    print(f' - page_content:\n {doc.page_content}')
                    print(f' - metadata: \n{doc.metadata}')
            print('\n================================')
            print('== Answer:\n\n' + answer['result'])

        else:
             print('Sorry')



        print('\033[m')

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('  - User exit.')
        sys.exit(1)