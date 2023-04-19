import os, sys
from langchain.llms import OpenAI

from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader
from langchain.document_loaders import DirectoryLoader

persist_directory = 'db'

# how to import .py too?
loader = DirectoryLoader('/Users/mark/dev/ml/openai-cookbook/', glob="*.md", loader_cls=TextLoader)
docs = loader.load()
if len(docs) == 0:
    print("No documents found")
    sys.exit()

print("Documents loaded:", len(docs))

# put text into a database
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=20)
texts = text_splitter.split_documents(docs)

embeddings = OpenAIEmbeddings()
docsearch = Chroma.from_documents(documents=texts, embedding=embeddings, persist_directory=persist_directory)
docsearch.persist()
