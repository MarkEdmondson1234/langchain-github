#!/Users/mark/dev/ml/langchain/read_github/langchain-github/env/bin/python
# change above to the location of your local Python venv installation
import os, sys, re
import pathlib
import argparse
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.callbacks import get_openai_callback

parser = argparse.ArgumentParser(description="Chat with a GitHub repository",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("repo", help="The GitHub repository on local disk")
parser.add_argument("--reindex", action="store_true", help="Whether to re-index the doc database that supply context to the Q&A")
parser.add_argument("--ext", help="Comma separated list of file extensions to include. Defaults to '.md,.py'")
parser.add_argument("--ignore", help="Directory to ignore file imports from. Defaults to 'env/'")
parser.add_argument("--resummarise", action="store_true", help="Recreate the code.md files describing the code")
args = parser.parse_args()
config = vars(args)

memory = ConversationBufferWindowMemory(k=2)
memory.chat_memory.add_user_message("You are an expert AI to help summarise code. You always enclose your code examples with three backticks (```)")
chat = ChatOpenAI(temperature=0.4)

def parse_code(code):
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
        memory.chat_memory.add_user_message("You MUST always enclose your code examples with three backticks (```)")
        return None
    
    return code, text

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

# Save generated code to a file
def save_to_file(filename, content, type="w"):
    with open(filename, type) as file:
        file.write(content)

# Function to summarise code from the OpenAI API     
def generate_code_summary(a_file):
    print("================================================")
    print(f"Requesting code summary for {a_file}   ")
    print("================================================")
    
    new_file_name = a_file.with_suffix('.md')
    if os.path.isfile(new_file_name) and not config['resummarise']:
         print(f"Skipping generating summary as found existing code summary file: {new_file_name}")
         return
    
    with open(a_file, "r") as file:
        code = file.read()

    # create prompt to pass in to LLM
    prompt = f"""Summarise what the code does below using Markdown syntax.  Comment on each function, and give some code examples of its uses: 
{code}
"""
    with get_openai_callback() as cb:
        chain = ConversationChain(
            llm=chat,
            #verbose=True,
            memory=memory)
        summary = chain.predict(input=prompt)
        print(cb)
    
    new_file_name = a_file.with_suffix('.md')

    ai = None
    result = parse_code(summary)
    if result is not None:
        response, ai = parse_code(summary)
    else:
         print("Got no code to parse")
         response = summary
    
    save_to_file(new_file_name, response)
    if ai:
        save_to_file(new_file_name, ai, type ="a")
    
    return
    
# Get source chunks from a repository
def get_source_chunks(repo_path, extension):
	source_chunks = []

	# Create a CharacterTextSplitter object for splitting the text
	splitter = CharacterTextSplitter(separator=" ", chunk_size=1024, chunk_overlap=0)
	for source in get_repo_docs(repo_path, extension):
		for chunk in splitter.split_text(source.page_content):
			source_chunks.append(Document(page_content=chunk, metadata=source.metadata))

	return source_chunks

def main():

	# Define the path of the repository and Chroma DB
	REPO_PATH =config['repo']
	CHROMA_DB_PATH = f'{os.getenv("CHROMA_DB_PATH", default = "./chroma/")}{os.path.basename(REPO_PATH)}'
	print("Chrome DB path: {}".format(CHROMA_DB_PATH))
	vector_db = None

	# Check if Chroma DB exists
	if not os.path.exists(CHROMA_DB_PATH) or config['reindex']:
		# Create a new Chroma DB
		print(f'Creating Chroma DB at {CHROMA_DB_PATH} ...')
		exts = '.md,.py'
		if config['ext']:
			exts = config['ext']
		source_chunks = get_source_chunks(REPO_PATH, exts)
		vector_db = Chroma.from_documents(source_chunks, OpenAIEmbeddings(), persist_directory=CHROMA_DB_PATH)
		vector_db.persist()

	else:
		# Load an existina Chroma DB
		print(f'Loading Chroma DB from {CHROMA_DB_PATH}.')
		vector_db = Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=OpenAIEmbeddings())

	# Load a QA chain
	qa = RetrievalQA.from_chain_type(
		llm=OpenAI(), 
		chain_type="stuff",
		retriever=vector_db.as_retriever(), 
		return_source_documents=True)
	
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
        print()
        print('User exited.')
        sys.exit(1)