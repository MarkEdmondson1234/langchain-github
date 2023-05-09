import os
import discord
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')  # Get your bot token from the .env file

client = discord.Client()

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!command'):
        # Forward the message content to your Flask app
        flask_app_url = 'http://localhost:5000/discord'
        payload = {
            'content': message.content
        }
        response = requests.post(flask_app_url, json=payload)

client.run(TOKEN)