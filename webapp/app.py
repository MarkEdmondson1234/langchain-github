import sys, os, requests

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

def send_document_to_index(uploaded_files, bucket_name):
    summaries = []
    os.makedirs('temp', exist_ok=True)
    for file in uploaded_files:
        # Save the file temporarily
        safe_filepath = os.path.abspath(os.path.join('temp', file.filename))
        logging.info(f'Saving file: {safe_filepath}')
        file.save(safe_filepath)
        try:
            # the original file split into chunks if necessary
            chunks = read_repo.add_single_file(safe_filepath, bucket_name, verbose=True)
            
            # a summary of the file
            summary = read_repo.summarise_single_file(safe_filepath, bucket_name, verbose=True)
            summaries.append(summary)
        finally:
            os.remove(safe_filepath)
    return summaries

@app.route('/process_files', methods=['POST'])
def process_files():
    
    bucket_name = os.getenv('GCS_BUCKET', None)
    logging.info(f"bucket: {bucket_name}")

    uploaded_files = request.files.getlist('files')
    if len(uploaded_files) > 0:
        logging.info('Upload form data')
        # we add document to the index
        summaries = send_document_to_index(uploaded_files, bucket_name)
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

@app.route('/discord', methods=['POST'])
def discord():
    data = request.get_json()
    user_input = data['content']  # Extract user input from the payload
    attachments = data.get('attachments', [])
    bucket_name = os.getenv('GCS_BUCKET', None)

    # Handle file attachments
    files = []
    for attachment in attachments:
        # Download the file and store it temporarily
        file_url = attachment['url']
        file_name = attachment['filename']
        response = requests.get(file_url)
        open(file_name, 'wb').write(response.content)
    
    if len(files) > 0:
        # send the file as a my_llm.langchain_class.PubSubChatMessageHistory
        bot_output = send_document_to_index(files, bucket_name)

    # Format the response payload
    response_payload = {
        "content": bot_output
    }

    # Send the response to the Discord webhook URL
    discord_webhook_url = os.getenv('DISCORD_URL')
    requests.post(discord_webhook_url, json=response_payload)

    return '', 204

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

