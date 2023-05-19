import sys, os, requests, json
import tempfile

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# app.py
from flask import Flask, render_template, request, jsonify
from qna import read_repo
from qna import question_service
from encoder_service import publish_to_pubsub_embed
from encoder_service import pubsub_chunk_to_store
import logging

app = Flask(__name__)

# can only take up to 10 minutes to ack
@app.route('/pubsub_chunk_to_store/<vector_name>', methods=['POST'])
def pubsub_to_doc(vector_name):
    if request.method == 'POST':
        data = request.get_json()

        try:
            # need to create a supabase table for each vector_name used
            meta = pubsub_chunk_to_store.pubsub_chunk_to_store(data, vector_name)
        except Exception as e:
            return jsonify({"Error": str(e)}), 503

        return jsonify({"Success": meta}), 200


@app.route('/pubsub_to_store/<vector_name>', methods=['POST'])
def pubsub_to_doc(vector_name):
    """
    splits up text or gs:// file into chunks and sends to pubsub topic 
      that pushes back to /pubsub_chunk_to_store/<vector_name>
    """
    if request.method == 'POST':
        data = request.get_json()

        try:
            # need to create a supabase table for each vector_name used
            meta = publish_to_pubsub_embed.data_to_embed_pubsub(data, vector_name)
        except Exception as e:
            return jsonify({"Error": str(e)}), 503

        return jsonify({"Success": meta}), 200


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
        content = "\n".join(chunks)
        safe_summary = f"{safe_filepath}.sum.txt"
        with open(safe_summary, 'w') as file:
            file.write(content)
        # a summary of the file
        summary = read_repo.summarise_single_file(safe_summary, bucket_name, verbose=True)
    finally:
        logging.info(f"Removing {safe_filepath}")
        os.remove(safe_filepath)
        os.remove(safe_summary)
    return summary

@app.route('/process_files', methods=['POST'])
def process_files():
    
    bucket_name = os.getenv('GCS_BUCKET', None)
    logging.info(f"bucket: {bucket_name}")

    uploaded_files = request.files.getlist('files')
    with tempfile.TemporaryDirectory() as temp_dir:
        summaries = []
        if len(uploaded_files) > 0:
            logging.info('Upload form data')
            for file in uploaded_files:
                logging.info(f'Uploading {file.filename}')
                
                # Save the file temporarily
                safe_filepath = os.path.join(temp_dir, file.filename)
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
    chat_history = data.get('chat_history', None)

    print(f"discord_message: {data}")

    if chat_history:
        # Separate the messages into human and AI messages
        human_messages = [message["content"] for message in chat_history if message["name"] == "Human"]
        ai_messages = [message["content"] for message in chat_history if message["name"] == "AI"]
        # Pair up the human and AI messages into tuples
        paired_messages = list(zip(human_messages, ai_messages))
    else:
        print("No chat history found")
        paired_messages = None

    bot_output = question_service.qna(user_input, "edmonbrain", chat_history=paired_messages)
    
    logging.info(f"bot_output: {bot_output}")

    # may be over 4000 char limit for discord but discord bot chunks it up for output
    return jsonify(bot_output)

@app.route('/discord/files', methods=['POST'])
def discord_files():
    data = request.get_json()
    attachments = data.get('attachments', [])
    bucket_name = os.getenv('GCS_BUCKET', None)

    with tempfile.TemporaryDirectory() as temp_dir:
        # Handle file attachments
        bot_output = []
        for attachment in attachments:
            # Download the file and store it temporarily
            file_url = attachment['url']
            file_name = attachment['filename']
            safe_file_name = os.path.join(temp_dir, file_name)
            response = requests.get(file_url)
            
            open(safe_file_name, 'wb').write(response.content)

            gs_file = publish_to_pubsub_embed.add_file_to_gcs(safe_file_name)
            meta = publish_to_pubsub_embed.data_to_embed_pubsub(gs_file, "edmonbrain")

            summary = send_document_to_index(safe_file_name, bucket_name)
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

