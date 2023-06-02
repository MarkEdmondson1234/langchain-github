from langchain.llms import VertexAI
from langchain import PromptTemplate, LLMChain

template = """Question: {question}

Answer: Let's think step by step."""

prompt = PromptTemplate(template=template, input_variables=["question"])

llm = VertexAI()

llm_chain = LLMChain(prompt=prompt, llm=llm)

question = "How many people were in the world at the time the Magna Carter was signed?"

answer = llm_chain.run(question)

print(answer)