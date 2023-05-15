import os
import discord
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')  # Get your bot token from the .env file
FLASKURL = os.getenv('FLASK_URL')
intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True

client = discord.Client(intents = intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    print("on_message")
    print(f"on_message.author: {message.author}")
    if message.author == client.user:
        return

    if message.content:
        print(f'Got the message: {message.content}')

        # Forward the message content to your Flask app
        flask_app_url = f'{FLASKURL}/discord/message'
        payload = {
            'content': message.content,
        }
        response = requests.post(flask_app_url, json=payload)
        if response.status_code == 204:
            await message.channel.send("Message has been processed successfully.")
        else:
            await message.channel.send("Error in processing message.")

    if message.attachments:
        # Forward the attachments to your Flask app
        flask_app_url = f'{FLASKURL}/discord/files'
        payload = {
            'attachments': [{'url': attachment.url, 'filename': attachment.filename} for attachment in message.attachments]
        }
        response = requests.post(flask_app_url, json=payload)
        if response.status_code == 204:
            await message.channel.send("File(s) have been uploaded to Electric Sheep successfully.")
        else:
            await message.channel.send("Error in processing file(s).")


client.run(TOKEN)