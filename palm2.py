import google.generativeai as palm # this wont work until have access to API key via MakerSuite

response = palm.generate_text(prompt="The opposite of hot is")
print(response.result) #  'cold.'
