import google.generativeai as palm
from google.auth import default
from google.auth.transport.requests import Request
from google.auth.exceptions import DefaultCredentialsError

# Define the scope
SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

try:
    # Obtain the default credentials
    creds, project = default(scopes=SCOPES)
    
    # If the credentials are expired, refresh them
    if creds and creds.expired:
        creds.refresh(Request())
except DefaultCredentialsError as e:
    print("Error: ", e)

response = palm.generate_text(prompt="The opposite of hot is")
print(response.result) #  'cold.'
