import os, sys
from glob import glob
from langchain.llms import OpenAI

from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
from langchain.indexes import VectorstoreIndexCreator

persist_directory = 'db'
dir = '/Users/mark/dev/ml/openai-cookbook/'

md_files = glob(dir + '**/*.md', recursive=True)
#py_files = glob(dir + '**/*.py', recursive=True) # needs different loader?
#files = py_files + md_files 
files = md_files

if len(files) == 0:
    print("No documents found")
    sys.exit()

loaders = [TextLoader(os.path.join(dir, fn)) for fn in files]

#loader = DirectoryLoader('/Users/mark/dev/ml/openai-cookbook/', glob="**/*.md", loader_cls=TextLoader)
#docs = loader.load()


print("Documents loaded:", len(files))

docsearch = VectorstoreIndexCreator(
    vectorstore_cls=Chroma,
    text_splitter=RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=20),
    embedding=OpenAIEmbeddings(),
    vectorstore_kwargs={"persist_directory": "db"}).from_loaders(loaders)

# put text into a database
#text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=20)
#texts = text_splitter.split_documents(docs)

#embeddings = OpenAIEmbeddings()
#docsearch = Chroma.from_documents(documents=texts, embedding=embeddings, persist_directory=persist_directory)
#docsearch.persist()
