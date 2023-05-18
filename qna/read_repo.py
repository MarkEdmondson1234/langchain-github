#!/Users/mark/dev/ml/langchain/read_github/langchain_github/env/bin/python
# change above to the location of your local Python venv installation
import sys, os, shutil

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

import pathlib

from langchain.docstore.document import Document
import langchain.text_splitter as text_splitter
from langchain.chat_models import ChatOpenAI
from my_llm import standards as my_llm
from my_llm.langchain_class import PubSubChatMessageHistory
from langchain import PromptTemplate
from langchain.document_loaders.unstructured import UnstructuredFileLoader

import logging

chat = ChatOpenAI(temperature=0)

CODE_EXTENSIONS = [".py", ".js", ".java", ".c", ".cpp", ".cc", ".cxx", ".hpp", 
                   ".h", ".cs", ".m", ".swift", ".go", ".rs", ".rb", ".php", 
                   ".pl", ".kt", ".kts", ".ts", ".scala", ".hs", ".lua", ".sh", 
                   ".bash", ".r", ".m", ".sql", ".html", ".css", ".xml", ".json",
                     ".yaml", ".yml"]

# Get Markdown documents from a repository
def get_repo_docs(repo_path, extension, memory, ignore=None, resummarise=False, verbose=False):
    repo = pathlib.Path(repo_path)

    ignore_path = ""
    if ignore is not None:
        ignore_path = repo / ignore
        if not ignore_path.is_dir():
            print("WARNING: --ignore must be a directory")
        
        print('Ignoring %s' % ignore_path)
    
    exts = extension.split(",")
    for ext in exts:
        the_glob = f"**/*{ext}"
        matched_files = list(repo.glob(the_glob))
        num_matched_files = len(matched_files)
        print(f"Number of matched {ext} files: {num_matched_files}")

        # Generate summary md files
        if ext!=".md":
            k = 0
            for non_md_file in repo.glob(the_glob):
                k += 1
                if str(non_md_file).startswith(str(ignore_path)):
                      continue
                generate_summary(non_md_file, memory, resummarise=resummarise, verbose=verbose)
                if verbose:
                    print(f"Generated summary for a {ext} file: {k} of {num_matched_files} done.")
                              
		# Iterate over all files in the repo (including subdirectories)
        print(f"Reading {ext} files")
        i = 0
        j = 0
        for md_file in repo.glob(the_glob):

            if str(md_file).startswith(str(ignore_path)):
                j += 1
                continue
            
            i += 1
			# Read the content of the file
            yield read_file_to_document(md_file)
            
            if verbose:
                print(f"Read {i} files so far and ignored {j}: total: {num_matched_files}")
        
        print(f"Read {i} and ignored {j} {ext} files.")
        
    print("Read all files")

def read_file_to_document(md_file, split=False, metadata: dict = None):
    try:
        loader = UnstructuredFileLoader(md_file)
        if split:
            # only supported for some file types
            docs = loader.load_and_split()
        else:
            docs = loader.load()
    except ValueError as e:
        if "file type is not supported in partition" in str(e):
            # Convert the file to .txt and try again
            txt_file = convert_to_txt(md_file)
            loader = UnstructuredFileLoader(txt_file)
            if split:
                docs = loader.load_and_split()
            else:
                docs = loader.load()
            os.remove(txt_file)  # Remove the temporary .txt file after processing
        else:
            raise e

    for doc in docs:
        if metadata is not None:
            doc.metadata.update(metadata)

    return docs

def convert_to_txt(file_path):
    file_dir, file_name = os.path.split(file_path)
    file_base, file_ext = os.path.splitext(file_name)
    txt_file = os.path.join(file_dir, f"{file_base}.txt")
    shutil.copyfile(file_path, txt_file)
    return txt_file

def code_prompt():
    # create prompt to pass in to LLM
    template = """
Summarise what the code does below.  Use Markdown in your output with the following template:

# a title
summary of script purpose

## keywords
Comma seperated list of 3-4 keywords suitable for this code

## classes
A description of each class

## functions/methods
How the functions or methods of a class work including listing the Inputs and outputs for each function

## code examples of use

The code to summarise is here:
{txt}
"""

    return PromptTemplate(
        input_variables=["txt"],
        template=template,
    )

def text_prompt():
    # create prompt to pass in to LLM
    template = """
Summarise the text below, and add some keywords at the bottom to describe the overall purpose of the text.
The text to summarise is here:
{txt}
"""

    return PromptTemplate(
        input_variables=["txt"],
        template=template,
    )

# Function to summarise code from the OpenAI API     
def generate_summary(a_file: pathlib.Path, memory, resummarise: bool=False, verbose: bool=False):
    
    if a_file.is_dir():
        raise ValueError(f"a_file must not be a directory: {a_file}")
    
    new_file_name = a_file.with_suffix('.md')
    if os.path.isfile(new_file_name) and not resummarise:
         if verbose:
            print(f"Skipping generating summary as found existing code summary file: {new_file_name}")
         return

    try:
        with open(a_file, "r") as file:
            file_text = file.read()
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        return
    
    if len(file_text) < 10:
        if verbose:
            print(f"Skipping generation as not enough information.  Got: {file_text}")
        return

    document = Document(page_content=file_text, metadata = {"source": os.path.abspath(a_file)})
    source_chunks = chunk_doc_to_docs([document], a_file.suffix)  

    code = True if str(a_file.suffix).lower() in CODE_EXTENSIONS else False

    if code:
        print("================================================")
        print(f"Requesting code summary for {a_file}   ")
        print("================================================")
        prompt = code_prompt()
    else:
        print("================================================")
        print(f"Requesting text summary for {a_file}   ")
        print("================================================")
        prompt = text_prompt()

    num_chunks = len(source_chunks)
    i=0
    for chunk in source_chunks:
        logging.info(f"Summarising chunk {i} of {num_chunks} of {a_file}")
        i += 1
        summary = my_llm.request_llm(
            prompt.format(txt=chunk.page_content), 
            chat, 
            memory,
            metadata={'task':'summarise_chunk'})
    
        my_llm.save_to_file(new_file_name, summary + '\n\n', type = "a")
    
    return pathlib.Path(new_file_name)
    
# Get source chunks from a repository
def get_source_docs(repo_path, extension, memory, ignore, resummarise, verbose):
    source_chunks = []

    for source in get_repo_docs(repo_path, 
                                extension=extension, 
                                memory=memory, 
                                ignore=ignore, 
                                resummarise=resummarise,
                                verbose=verbose):
        
        splitter = choose_splitter(extension)
        for chunk in splitter.split_text(source.page_content):
            source_chunks.append(Document(page_content=chunk, metadata=source.metadata))

    return source_chunks

def choose_splitter(extension: str, chunk_size: int=1024, chunk_overlap:int=0):
    if extension == ".py":
        return text_splitter.PythonCodeTextSplitter()
    elif extension == ".md":
        return text_splitter.MarkdownTextSplitter()
    
    return text_splitter.RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def setup_memory(config):

    memory = PubSubChatMessageHistory("qna_documents")

    if config.get('bucket_name', None) is not None:
        memory.set_bucket(config.get('bucket_name'))
        memory.load_vectorstore_memory()

    if config['reindex']:
		# Create a new Chroma DB
        exts = '.md,.py'
        if config['ext']:
            exts = config['ext']
        source_chunks = get_source_docs(config['repo'], 
                                        extension=exts, 
                                        memory=memory, 
                                        ignore=config['ignore'], 
                                        resummarise=config['resummarise'],
                                        verbose=config['verbose'])
        memory.save_vectorstore_memory(source_chunks, verbose=config['verbose'])

    return memory 


def document_to_dict(document):
    return {
        'page_content': document.page_content,
        'metadata': document.metadata,
    }

def process_input(user_input: str, 
                  verbose: bool =True,
                  bucket_name: str = None,
                  chat_history = None):

    # more only needed if you need to recreate the vectorstore which we wont with web app
    config = {
        'reindex': False,
        'bucket_name': bucket_name
    }
        
    if verbose:
        print(f"user_input: {user_input}")
        print(f"process_input config: {config}")
    logging.info(f"user_input: {user_input}")
    logging.info(f"process_input config: {config}")
    
    memory = setup_memory(config)
    answer = memory.question_memory(user_input, 
                                    llm=chat, 
                                    verbose=verbose,
                                    chat_history = chat_history)

    response = {'result': 'No answer found'}
    if answer is not None:
        response = {'result': answer['result']}
        if answer.get('source_documents') is not None:
            source_documents = [document_to_dict(doc) for doc in answer['source_documents']]
            response['source_documents'] = source_documents
        else:
            logging.info('No source documents found')

    return response

def add_single_file(filename: str, bucket_name, verbose=False):
    config = {
        'reindex': False, # as we will trigger file summary directly
        'bucket_name': bucket_name
    }
    filename = pathlib.Path(filename)
    if not filename.is_file():
        raise ValueError(f"Filename was not a valid file path: {filename}")
    
    docs = read_file_to_document(filename)
    chunks = chunk_doc_to_docs(docs, filename.suffix)

    memory = setup_memory(config)

    docs_output = []
    chunk_length = len(chunks)
    i = 0
    for chunk in chunks:
        logging.info(f"Uploading chunk {i} of size {chunk_length} for {filename.name}")
        i+=1
        memory.add_user_message(chunk.page_content, 
                                metadata={"task": "singlefile load original",
                                          "source": filename.name})
        docs_output.append(chunk.page_content)
    
    return docs_output


def summarise_single_file(filename: str, bucket_name, verbose=False):
    config = {
        'reindex': False, # as we will trigger file summary directly
        'bucket_name': bucket_name
    }

    filename = pathlib.Path(filename)
    if not filename.is_file():
        raise ValueError(f"Filename was not a valid file path: {filename}")

    memory = setup_memory(config)

    summary_filename = generate_summary(filename, 
                                        memory, 
                                        resummarise=True, 
                                        verbose=verbose)
    
    if not summary_filename:
        return f"No summary generated for {str(filename)}"    

    documents = read_file_to_document(summary_filename)
    chunks = chunk_doc_to_docs(documents, filename.suffix)

    output_content = ""
    for chunk in chunks:
        memory.add_user_message(chunk.page_content, 
                                metadata={"task": "singlefile load summary",
                                          "source": filename.name})
        output_content += chunk.page_content + "\n\n"

    return output_content

def chunk_doc_to_docs(documents: list, extension: str = ".md"):
    """Turns a Document object into a list of many Document chunks"""
    for document in documents:
        source_chunks = []
        splitter = choose_splitter(extension)
        for chunk in splitter.split_text(document.page_content):
            source_chunks.append(Document(page_content=chunk, metadata=document.metadata))

        return source_chunks  
    
    

def main(config):

    memory = setup_memory(config)
	
    while True:
        print('\n\033[31m' + '=Ask a question. CTRL + C to quit.')
        print ("=If I don't know, tell me the right answer so I can learn and answer more accurately next time"  + '\033[m')
        user_input = input()
        print('\033[31m')
        answer = memory.question_memory(user_input, llm=chat, verbose=config['verbose'])
        if answer is not None:
            if answer.get('source_documents') is not None:
                print('\n== Document sources:')
                i = 0
                for doc in answer.get('source_documents'):
                    i += 1
                    print(f'-- Source {i}')
                    print(f' - page_content:\n {doc.page_content}')
                    if config['verbose']:
                        print(f' - metadata: \n{doc.metadata}')

            print('\n================================')
            print('== Answer:\n\n' + answer['result'])

        else:
             print('Sorry')

        print('\033[m')


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser(description="Chat with a GitHub repository",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("repo", help="The GitHub repository on local disk")
    parser.add_argument("--reindex", action="store_true", 
                        help="Whether to re-index the doc database that supply context to the Q&A")
    parser.add_argument("--ext", help="Comma separated list of file extensions to include. Defaults to '.md,.py'")
    parser.add_argument("--ignore", help="Directory to ignore file imports from. Defaults to 'env/'")
    parser.add_argument("--resummarise", action="store_true", help="Recreate the code.md files describing the code")
    parser.add_argument("--verbose", action="store_true", help="Include metadata such as sources in replies")
    parser.add_argument("--bucket", help="A Google Cloud Storage bucket name e.g. ga://your-bucket-name")
    args = parser.parse_args()
    config = vars(args)

    try:
        main(config)
    except KeyboardInterrupt:
        print('  - User exit.')
        sys.exit(1)