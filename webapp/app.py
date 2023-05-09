import sys, os, requests

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# app.py
from flask import Flask, render_template, request, jsonify
from qna import read_repo

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/process_input', methods=['POST'])
def process_input():
    data = request.get_json()
    user_input  = data.get('user_input')
    repo        = data.get('repo', None)
    reindex     = data.get('reindex', False)
    ext         = data.get('ext', '.py,.md')
    ignore      = data.get('ignore', 'env/')
    resummarise = data.get('resummarise', False)

    bot_output = read_repo.process_input(user_input, repo, reindex, ext, ignore, resummarise)
    return bot_output

@app.route('/discord', methods=['POST'])
def discord():
    data = request.get_json()
    user_input = data['content']  # Extract user input from the payload
    attachments = data.get('attachments', [])

    # Handle file attachments
    files = []
    for attachment in attachments:
        # Download the file and store it temporarily
        file_url = attachment['url']
        file_name = attachment['filename']
        response = requests.get(file_url)
        open(file_name, 'wb').write(response.content)

        # Add the file to the list of files to be sent back
        files.append(('files', (file_name, open(file_name, 'rb'))))
    
    if len(files) > 0:
        # send the file as a my_llm.langchain_class.PubSubChatMessageHistory
        pass

    # Process the input and get the bot's response
    bot_output = read_repo.process_input(user_input)

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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

