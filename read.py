import os, sys
from langchain.llms import OpenAI

from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.indexes.vectorstore import VectorStoreIndexWrapper

persist_directory = 'db'

embeddings = OpenAIEmbeddings()
docsearch = Chroma(embedding_function=embeddings, persist_directory=persist_directory)

qa = RetrievalQA.from_chain_type(llm=OpenAI(), chain_type="stuff", retriever=docsearch.as_retriever())

query = "When GPT-3 fails on a task, what should you do?"

context = docsearch.as_retriever().get_relevant_documents(query)
print("================================")
print("CONTEXT:")
print(context)

print("================================")
print("PROMPT:")
answer = qa.run(query)

print(answer)



print("================================")
print("PROMPT2:")

index = VectorStoreIndexWrapper(
    vectorstore_cls=Chroma,
    embedding=OpenAIEmbeddings(),
    vectorstore_kwargs={"persist_directory": "db"})

answer2 = index.query_with_sources(query)
print(answer2)
