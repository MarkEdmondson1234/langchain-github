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
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
        await channel.send(chunk)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content:
        print(f'Got the message: {message.content}')

        # Send a thinking message
        thinking_message = await message.channel.send("Thinking...")

        history = []
        async for msg in message.channel.history(limit=10):
            history.append(msg)

        # Reverse the messages to maintain the order of conversation
        chat_history = [{"name": "AI" if msg.author == client.user \
                            else "Human", "content": msg.content} \
                            for msg in reversed(history[1:])]

        print(f"Chat history: {chat_history}")

        # Forward the message content to your Flask app
        flask_app_url = f'{FLASKURL}/discord/message'
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
                    for source in source_docs:
                        source_message = f"Source: {source.get('page_content')}\nMetadata: {source.get('metadata')}"
                        await chunk_send(message.channel, source_message)
                    # Edit the thinking message to show the reply
                    await thinking_message.edit(content=reply_content)
                else:
                    # Edit the thinking message to show an error
                    await thinking_message.edit(content="Error in processing message.")

    if message.attachments:
        # Send a thinking message
        thinking_message = await message.channel.send("Uploading file(s)...1Gb limit...")

        # Forward the attachments to your Flask app
        flask_app_url = f'{FLASKURL}/discord/files'
        payload = {
            'attachments': [{'url': attachment.url, 'filename': attachment.filename} for attachment in message.attachments]
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(flask_app_url, json=payload) as response:
                print(f'file response.status: {response.status}')
                if response.status == 204:
                    # Edit the thinking message to show the reply
                    await thinking_message.edit(content='File successfully entered into brain.')
                if response.status == 200:
                    response_data = await response.json()
                    print(f'response_data: {response_data}')
                    summaries = response_data.get('summaries', [])
                    for summary in summaries:
                        await chunk_send(message.channel, summary)
                    await thinking_message.edit(content="Uploaded file and generated summaries")
                else:
                    # Edit the thinking message to show an error
                    await thinking_message.edit(content="Error in processing file(s).")

client.run(TOKEN)
