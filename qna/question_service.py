import os, logging

from langchain.vectorstores import SupabaseVectorStore
from langchain.embeddings import OpenAIEmbeddings
from langchain.llms import OpenAI

#https://python.langchain.com/en/latest/modules/chains/index_examples/chat_vector_db.html
from langchain.chains import ConversationalRetrievalChain

from supabase import Client, create_client
from dotenv import load_dotenv

load_dotenv()

def qna(question: str, vector_name: str, chat_history=None):

    logging.info("Initiating Supabase store")
    # init embedding and vector store
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    logging.info(f"Supabase URL: {supabase_url}")
    embeddings = OpenAIEmbeddings()
    supabase: Client = create_client(supabase_url, supabase_key)

    vectorstore = SupabaseVectorStore(supabase, embeddings, table_name=vector_name)

    retriever = vectorstore.as_retriever(search_kwargs=dict(k=4))

    llm = OpenAI(temperature=0)

    qa = ConversationalRetrievalChain.from_llm(llm, retriever=retriever, return_source_documents=True)

    result = qa({"question": question, "chat_history": chat_history})
    
    return result