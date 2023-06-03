import sys, os, requests
import tempfile
import datetime

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# app.py
from flask import Flask, render_template, request, jsonify
from qna import question_service
from encoder_service import publish_to_pubsub_embed
from encoder_service import pubsub_chunk_to_store as pb
import logging
import bot_help

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/reindex', methods=['GET'])
def reindex():
    return render_template('reindex.html')

@app.route('/process_files', methods=['POST'])
def process_files():
    bucket_name = os.getenv('GCS_BUCKET', None)
    logging.info(f"bucket: {bucket_name}")

    uploaded_files = request.files.getlist('files')
    with tempfile.TemporaryDirectory() as temp_dir:
        vector_name = "edmonbrain"
        summaries = bot_help.handle_files(uploaded_files, temp_dir, vector_name)
        return jsonify({"summaries": summaries if summaries else ["No files were uploaded"]})

app_chat_history = []

@app.route('/process_input', methods=['POST'])
def process_input():
    # json input
    data = request.get_json()
    logging.info(f'Request data: {data}')

    user_input  = data.get('user_input', '')
    vector_name = 'edmonbrain' # replace with your vector name

    paired_messages = bot_help.extract_chat_history(app_chat_history)

    # ask the bot a question about the documents in the vectorstore
    bot_output = question_service.qna(user_input, vector_name, chat_history=paired_messages)

    # append user message to chat history
    app_chat_history.append({'name': 'Human', 'content': user_input})
    
    # append bot message to chat history
    app_chat_history.append({'name': 'AI', 'content': bot_output['answer']})

    logging.info(f"bot_output: {bot_output}")

    return jsonify(bot_help.generate_output(bot_output))


@app.route('/discord/<vector_name>/message', methods=['POST'])
def discord_message(vector_name):
    data = request.get_json()
    user_input = data['content'].strip()  # Extract user input from the payload

    logging.info(f"discord_message: {data}")

    now = datetime.datetime.now()
    hourmin = now.strftime("%H%M")

    chat_history = data.get('chat_history', None)
    paired_messages = bot_help.extract_chat_history(chat_history)

    if user_input.startswith("!savethread"):
        # write chat history to a file
        with tempfile.TemporaryDirectory() as temp_dir:
            chat_file_path = os.path.join(temp_dir, f"{hourmin}_chat_history.txt")
            with open(chat_file_path, 'w') as file:
                for chat in chat_history:
                    file.write(f"{chat['name']}: {chat['content']}\n")
            gs_file = bot_help.app_to_store(chat_file_path, vector_name, via_bucket_pubsub=True)
            result = {"result": f"Saved chat history to {gs_file}"}

            return result
    
    if user_input.startswith("!saveurl"):
        if publish_to_pubsub_embed.contains_url(user_input):
            urls = publish_to_pubsub_embed.extract_urls(user_input)
            for url in urls:
                publish_to_pubsub_embed.publish_text(url, vector_name)
            result = {"result": f"URLs sent for processing: {urls}"}
        else:
            result = {"result": f"No URLs were found"}
        return jsonify(result)
    
    if user_input.startswith("!deletesource"):
        source = user_input.replace("!deletesource", "")
        source = source.replace("source:","").strip()
        publish_to_pubsub_embed.delete_source(source, vector_name=vector_name)
        result = {"result": f"Deleting source: {source}"}
        return jsonify(result)
    
    if user_input.startswith("!sources"):
        rows = publish_to_pubsub_embed.return_sources_last24_(vector_name)

        if rows is None:
            result = {"result": "No sources were found"}
        else:
            msg = "\n".join([f"{row}" for row in rows])
            result = {"result": f"*sources:*\n{msg}"}

        return jsonify(result)
    
    if user_input.startswith("!help"):
        result = {"result":f"""* `!sources` - get sources added in last 24hrs
* `!deletesource [gs:// source]` - delete a source from database
* `!saveurl [https:// url]` - add the contents found at this URL to database
* `!savethread` - save current Discord thread as a source to database
* `!help`- see this message
* Files attached to messages will be added as source to database
"""}
        return jsonify(result)

    bot_output = question_service.qna(user_input, vector_name, chat_history=paired_messages)
    
    logging.info(f"bot_output: {bot_output}")
    
    discord_output = bot_help.generate_output(bot_output)

    # may be over 4000 char limit for discord but discord bot chunks it up for output
    return jsonify(discord_output)

@app.route('/discord/<vector_name>/files', methods=['POST'])
def discord_files(vector_name):
    data = request.get_json()
    attachments = data.get('attachments', [])
    content = data.get('content', "").strip()
    chat_history = data.get('chat_history', [])

    logging.info(f'discord_files got data: {data}')
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

            gs_file = bot_help.app_to_store(safe_file_name, 
                                            vector_name, 
                                            via_bucket_pubsub=True, 
                                            metadata={'discord_comment': content})
            bot_output.append(f"{file_name} uploaded to {gs_file}")

    # Format the response payload
    response_payload = {
        "summaries": bot_output
    }

    return response_payload, 200

# can only take up to 10 minutes to ack
@app.route('/pubsub_chunk_to_store/<vector_name>', methods=['POST'])
def pubsub_chunk_to_store(vector_name):
    """
    Final PubSub destination for each chunk that sends data to Supabase vectorstore"""
    if request.method == 'POST':
        data = request.get_json()

        meta = pb.from_pubsub_to_supabase(data, vector_name)

        return {'status': 'Success'}, 200


@app.route('/pubsub_to_store/<vector_name>', methods=['POST'])
def pubsub_to_store(vector_name):
    """
    splits up text or gs:// file into chunks and sends to pubsub topic 
      that pushes back to /pubsub_chunk_to_store/<vector_name>
    """
    if request.method == 'POST':
        data = request.get_json()

        meta = publish_to_pubsub_embed.data_to_embed_pubsub(data, vector_name)
        file_uploaded = str(meta.get("source", "Could not find a source"))
        return jsonify({'status': 'Success', 'source': file_uploaded}), 200

@app.route('/pubsub_to_discord', methods=['POST'])
def pubsub_to_discord():
    if request.method == 'POST':
        data = request.get_json()
        message_data = bot_help.process_pubsub(data)
        if isinstance(message_data, str):
            the_data = message_data
        elif isinstance(message_data, dict):
            if message_data.get('status', None) is not None:
                cloud_build_status = message_data.get('status')
                the_data = {'type': 'cloud_build', 'status': cloud_build_status}
                if cloud_build_status not in ['SUCCESS','FAILED']:
                    return cloud_build_status, 200

        response = bot_help.discord_webhook(the_data)

        if response.status_code != 204:
            logging.info(f'Request to discord returned {response.status_code}, the response is:\n{response.text}')
        
        return 'ok', 200

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
            bot_output = None #TODO 

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

