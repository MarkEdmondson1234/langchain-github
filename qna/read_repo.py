#!/Users/mark/dev/ml/langchain/read_github/langchain_github/env/bin/python
# change above to the location of your local Python venv installation
import sys, os

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

import pathlib
import argparse
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from my_llm import standards as my_llm

parser = argparse.ArgumentParser(description="Chat with a GitHub repository",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("repo", help="The GitHub repository on local disk")
parser.add_argument("--reindex", action="store_true", help="Whether to re-index the doc database that supply context to the Q&A")
parser.add_argument("--ext", help="Comma separated list of file extensions to include. Defaults to '.md,.py'")
parser.add_argument("--ignore", help="Directory to ignore file imports from. Defaults to 'env/'")
parser.add_argument("--resummarise", action="store_true", help="Recreate the code.md files describing the code")
args = parser.parse_args()
config = vars(args)

memory = my_llm.init_memory("read_repo")
memory.add_user_message("You are an expert AI to help summarise code. You always enclose your code examples with three backticks (```)")
chat = ChatOpenAI(temperature=0.4)

# Get Markdown documents from a repository
def get_repo_docs(repo_path, extension):
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
                generate_code_summary(non_md_file)
                              
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
def generate_code_summary(a_file):
    
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
         print(f"Skipping generation as not enough information.  Got: {code}")
         return

    # create prompt to pass in to LLM
    prompt = f"""Summarise what the code does below using Markdown syntax.  Comment on each function, and give some code examples of its uses: 
{code}
"""
    summary = my_llm.request_llm(prompt, chat, memory)
    
    new_file_name = a_file.with_suffix('.md')

    ai = None
    result = my_llm.parse_code(summary, memory)
    if result is not None:
        response = result
    else:
        print("Got no code to parse")
        response = summary
    
    my_llm.save_to_file(new_file_name, response)
    if ai:
        my_llm.save_to_file(new_file_name, ai, type ="a")
    
    return
    
# Get source chunks from a repository
def get_source_chunks(repo_path, extension):
	source_chunks = []

	# Create a CharacterTextSplitter object for splitting the text
    # TODO: For .py files use https://python.langchain.com/en/latest/modules/indexes/text_splitters/examples/python.html
	splitter = CharacterTextSplitter(separator=" ", chunk_size=1024, chunk_overlap=0)
	for source in get_repo_docs(repo_path, extension):
		for chunk in splitter.split_text(source.page_content):
			source_chunks.append(Document(page_content=chunk, metadata=source.metadata))

	return source_chunks

def main():

    # Define the path of the repository and Chroma DB
    REPO_PATH =config['repo']
    CHROMA_DB_PATH = f'{os.getenv("CHROMA_DB_PATH")}/read_repo/{os.path.basename(REPO_PATH)}'
    print("Chrome DB path: {}".format(CHROMA_DB_PATH))
    vector_db = None

	# Check if Chroma DB exists
    if not os.path.exists(CHROMA_DB_PATH) or config['reindex']:
		# Create a new Chroma DB
        exts = '.md,.py'
        if config['ext']:
            exts = config['ext']
        source_chunks = get_source_chunks(REPO_PATH, exts)
        vector_db = my_llm.new_vector_db(CHROMA_DB_PATH, source_chunks)

    else:
		# Load an existing Chroma DB
        vector_db = my_llm.load_vector_db(CHROMA_DB_PATH)
    
    if vector_db:

        # Load a QA chain
        qa = RetrievalQA.from_chain_type(
            llm=OpenAI(), 
            chain_type="stuff",
            retriever=vector_db.as_retriever(), 
            return_source_documents=True)
    else:
         print("Error creating vector database")
         sys.exit(1)
	
    while True:
        print('\n\033[31m' + 'Ask a question. CTRL + C to quit.' + '\033[m')
        user_input = input()
        print('\033[31m')
        answer = qa({"query": user_input})
        print('Answer:' + answer['result'])

        print('== Document sources:')
        for doc in answer['source_documents']:
            print(' - ' + doc.metadata['source'])

        print('\033[m')

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('  - User exit.')
        sys.exit(1)