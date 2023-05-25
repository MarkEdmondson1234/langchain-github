import os
from encoder_service import publish_to_pubsub_embed
import logging
import base64
import json
import requests

def discord_webhook(message_data):
    webhook_url = os.getenv('DISCORD_URL', None)  # replace with your webhook url
    if webhook_url is None:
        return None
    
    logging.info(f'webhook url: {webhook_url}')

    # If the message_data is not a dict, wrap it in a dict.
    if not isinstance(message_data, dict):
        message_data = {'content': message_data}
    else:
        # if it is a dict, turn it into a string
        message_data = {'content': json.dumps(message_data)}
        #TODO parse out message_data into other discord webhook objects like embed
        # https://birdie0.github.io/discord-webhooks-guide/discord_webhook.html
    
    data = message_data

    logging.info(f'Sending discord this data: {data}')
    response = requests.post(webhook_url, json=data,
                            headers={'Content-Type': 'application/json'})
    logging.info(f'Sent data to discord: {response}')
    
    return response

def process_pubsub(data):

    logging.info(f'process_pubsub: {data}')
    message_data = base64.b64decode(data['message']['data']).decode('utf-8')
    messageId = data['message'].get('messageId')
    publishTime = data['message'].get('publishTime')

    logging.info(f"This Function was triggered by messageId {messageId} published at {publishTime}")
    #logging.info(f"bot_help.process_pubsub message data: {message_data}")

    try:
        message_data = json.loads(message_data)
    except:
        logging.debug("Its not a json")

    if message_data:
        return message_data
    
    logging.info(f"message_data was empty")
    return ''

def app_to_store(safe_file_name, vector_name, via_bucket_pubsub=False, metadata:dict=None):
    
    gs_file = publish_to_pubsub_embed.add_file_to_gcs(safe_file_name, vector_name, metadata=metadata)

    # we send the gs:// to the pubsub ourselves
    if not via_bucket_pubsub:
        publish_to_pubsub_embed.publish_text(gs_file, vector_name)

    return gs_file
    
def handle_files(uploaded_files, temp_dir, vector_name):
    bot_output = []
    if uploaded_files:
        for file in uploaded_files:
            # Save the file temporarily
            safe_filepath = os.path.join(temp_dir, file.filename)
            file.save(safe_filepath)

            app_to_store(safe_filepath, vector_name)
            bot_output.append(f"{file.filename} sent to {vector_name}")

    return bot_output

def generate_output(bot_output):
    source_documents = []
    if bot_output.get('source_documents', None) is not None:
        source_documents = []
        for doc in bot_output['source_documents']:
            metadata = doc.metadata
            filtered_metadata = {}
            if metadata.get("source", None) is not None:
                filtered_metadata["source"] = metadata["source"]
            if metadata.get("type", None) is not None:
                filtered_metadata["type"] = metadata["type"]
            source_doc = {
                'page_content': doc.page_content,
                'metadata': filtered_metadata
            }
            source_documents.append(source_doc)

    return {
        'result': bot_output.get('answer', "No answer available"),
        'source_documents': source_documents
    }

def embeds_to_json(message):
    return json.dumps(message["embeds"]) if message["embeds"] else None

def create_message_element(message):
    return (message["content"] + 'Embeds: ' + embeds_to_json(message) if embeds_to_json(message) else message["content"])

def is_human(message):
    return message["name"] == "Human"

def is_ai(message):
    return message["name"] == "AI"

def extract_chat_history(chat_history=None):
    
    if chat_history:
        # Separate the messages into human and AI messages
        human_messages = [create_message_element(message) for message in chat_history if is_human(message)]
        ai_messages = [create_message_element(message) for message in chat_history if is_ai(message)]
        # Pair up the human and AI messages into tuples
        paired_messages = list(zip(human_messages, ai_messages))
    else:
        print("No chat history found")
        paired_messages = []

    return paired_messages