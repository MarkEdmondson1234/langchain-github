import sys, os, requests, json

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# app.py
from flask import Flask, render_template, request, jsonify
from qna import read_repo
import logging

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/reindex', methods=['GET'])
def reindex():
    return render_template('reindex.html')

def send_document_to_index(safe_filepath:str, bucket_name):

    try:
        # the original file split into chunks if necessary
        chunks = read_repo.add_single_file(safe_filepath, bucket_name, verbose=True)
        # a summary of the file
        summary = read_repo.summarise_single_file(safe_filepath, bucket_name, verbose=True)
    finally:
        logging.info(f"Removing {safe_filepath}")
        os.remove(safe_filepath)
    return summary

@app.route('/process_files', methods=['POST'])
def process_files():
    
    bucket_name = os.getenv('GCS_BUCKET', None)
    logging.info(f"bucket: {bucket_name}")

    uploaded_files = request.files.getlist('files')
    os.makedirs('temp', exist_ok=True)
    summaries = []
    if len(uploaded_files) > 0:
        logging.info('Upload form data')
        for file in uploaded_files:
            logging.info(f'Uploading {file.filename}')
            
            # Save the file temporarily
            safe_filepath = os.path.abspath(os.path.join('temp', file.filename))
            logging.info(f'Saving file: {safe_filepath}')
            file.save(safe_filepath)

            # we add document to the index
            summary = send_document_to_index(safe_filepath, bucket_name)
            summaries.append(summary)

        return jsonify({"summaries": summaries})
    
    return jsonify({"summaries": ["No files were uploaded"]})

@app.route('/process_input', methods=['POST'])
def process_input():
    
    bucket_name = os.getenv('GCS_BUCKET', None)

    # json input
    data = request.get_json()
    logging.info(f'Request data: {data}')

    user_input  = data.get('user_input', '')
    # we ask the bot a question about the documents in the vectorstore
    bot_output = read_repo.process_input(
        user_input=user_input,
        verbose=True,
        bucket_name=bucket_name)
    
    logging.info(f"bot_output: {bot_output}")
    
    return bot_output

@app.route('/discord/message', methods=['POST'])
def discord_message():
    data = request.get_json()
    user_input = data['content']  # Extract user input from the payload
    bucket_name = os.getenv('GCS_BUCKET', None)

    # we ask the bot a question about the documents in the vectorstore
    bot_output = read_repo.process_input(
        user_input=user_input,
        verbose=True,
        bucket_name=bucket_name)
    
    logging.info(f"bot_output: {bot_output}")

    # Ensure the message doesn't exceed Discord's character limit
    result = bot_output.get('result', '')
    source_documents = bot_output.get('source_documents', [])

    # Convert result and source_documents to a string representation to count characters
    result_str = json.dumps(result)
    source_documents_str = json.dumps(source_documents)

    total_length = len(result_str) + len(source_documents_str)
    if total_length > 4000:
        # Remove documents from the end until the total length is under 4000 characters
        while total_length > 4000 and source_documents:
            source_documents.pop()
            source_documents_str = json.dumps(source_documents)
            total_length = len(result_str) + len(source_documents_str)

        bot_output['source_documents'] = source_documents

    return jsonify(bot_output)

@app.route('/discord/files', methods=['POST'])
def discord_files():
    data = request.get_json()
    attachments = data.get('attachments', [])
    bucket_name = os.getenv('GCS_BUCKET', None)

    # Handle file attachments
    bot_output = []
    for attachment in attachments:
        # Download the file and store it temporarily
        file_url = attachment['url']
        file_name = attachment['filename']
        response = requests.get(file_url)
        open(file_name, 'wb').write(response.content)
        summary = send_document_to_index(file_name, bucket_name)
        bot_output.append(summary)

    # Format the response payload
    response_payload = {
        "summaries": bot_output
    }

    return response_payload, 200

@app.route('/slack', methods=['POST'])
def slack():
    data = request.form
    if data.get('type') == 'url_verification':  # Respond to Slack's URL verification challenge
        return jsonify({'challenge': data['challenge']})
    
    if data.get('type') == 'event_callback':
        event = data['event']
        if event['type'] == 'app_mention':  # The bot was mentioned in the message
            user_input = event['text']
            # Process the input and get the bot's response
            bot_output = read_repo.process_input(user_input)
            
            # Format the response payload
            response_payload = {
                "text": bot_output
            }
            
            # Send the response to the Slack channel
            slack_api_url = 'https://slack.com/api/chat.postMessage'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {os.environ["SLACK_BOT_TOKEN"]}'
            }
            requests.post(slack_api_url, headers=headers, json=response_payload)
    
    return '', 204



if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)

