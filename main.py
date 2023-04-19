import os, sys
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


prompt = PromptTemplate(
    input_variables=["q"],
    template="In Python, how do you {q}? Give an example",
)

print ('Hello World: ', os.environ["OPENAI_API_KEY"])

llm = OpenAI(temperature=0)

question = "input a glob that will catch all .md and .py files"
print(prompt.format(q=question))

chain = LLMChain(llm=llm, prompt=prompt)

answer = chain.run(question)
print(answer)
