import os
import discord
import aiohttp
import json
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')  # Get your bot token from the .env file
FLASKURL = os.getenv('FLASK_URL')
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True  # Enable DM messages

client = discord.Client(intents=intents)

async def chunk_send(channel, message):
    chunks = [message[i:i+1500] for i in range(0, len(message), 1500)]
    for chunk in chunks:
        await channel.send(chunk)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if client.user not in message.mentions:
        return

    if message.content:
        print(f'Got the message: {message.content}')

        # Start a new thread with the received message
        new_thread = await message.start_thread(name="Edmonbrain thread")

        # Send a thinking message
        thinking_message = await new_thread.send("Thinking...")

        history = []
        async for msg in message.channel.history(limit=10):
            history.append(msg)

        # Reverse the messages to maintain the order of conversation
        chat_history = [{"name": "AI" if msg.author == client.user \
                            else "Human", "content": msg.content} \
                            for msg in reversed(history[1:])]

        print(f"Chat history: {chat_history}")

        # Forward the message content to your Flask app
        flask_app_url = f'{FLASKURL}/discord/edmonbrain/message'
        print(f'Calling {flask_app_url}')
        payload = {
            'content': message.content,
            'chat_history': chat_history
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(flask_app_url, json=payload) as response:
                print(f'chat response.status: {response.status}')
                if response.status == 200:
                    response_data = await response.json()  # Get the response data as JSON
                    print(f'response_data: {response_data}')

                    source_docs = response_data.get('source_documents', [])
                    reply_content = response_data.get('result')  # Get the 'result' field from the JSON

                    seen = set()
                    unique_source_docs = []

                    for source in source_docs:
                        metadata_str = json.dumps(source.get('metadata'), sort_keys=True)
                        if metadata_str not in seen:
                            unique_source_docs.append(source)
                            seen.add(metadata_str)

                    for source in unique_source_docs:
                        source_message = f"*source metadata*: {source.get('metadata')}"
                        await chunk_send(new_thread source_message)

                    # Edit the thinking message to show the reply
                    await new_thread.edit(content=reply_content)
                else:
                    # Edit the thinking message to show an error
                    await new_thread.edit(content="Error in processing message.")

    if message.attachments:
        # Start a new thread with the received message
        new_thread2 = await message.start_thread(name="Edmonbrain upload")

        # Send a thinking message
        thinking_message = await new_thread2.send("Uploading file(s)..")

        # Forward the attachments to Flask app
        flask_app_url = f'{FLASKURL}/discord/edmonbrain/files'
        print(f'Calling {flask_app_url}')
        payload = {
            'attachments': [{'url': attachment.url, 'filename': attachment.filename} for attachment in message.attachments]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(flask_app_url, json=payload) as response:
                print(f'file response.status: {response.status}')
                if response.status == 200:
                    response_data = await response.json()
                    print(f'response_data: {response_data}')
                    summaries = response_data.get('summaries', [])
                    for summary in summaries:
                        await chunk_send(new_thread2, summary)
                    await thinking_message.edit(content="Uploaded file(s)")
                else:
                    # Edit the thinking message to show an error
                    await thinking_message.edit(content="Error in processing file(s).")

client.run(TOKEN)
