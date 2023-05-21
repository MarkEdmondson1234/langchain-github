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

    print(message)

    if message.content:
        print(f'Got the message: {message.content}')

        bot_mention = client.user.mention
        clean_content = message.content.replace(bot_mention, '')

        # Check if the message was sent in a thread or a private message
        if isinstance(message.channel, (discord.Thread, discord.DMChannel)):
            new_thread = message.channel
        else:
            # If it's not a thread, create a new one
            new_thread = await message.channel.create_thread(
                name=clean_content[:30], 
                message=message)


        # Send a thinking message
        thinking_message = await new_thread.send("Thinking...")

        history = []
        async for msg in new_thread.history(limit=50):
            if msg.content.startswith(f"Reply to {bot_mention}"):
                continue
            if msg.content.startswith("Use !savethread"):
                continue
            history.append(msg)

        # Reverse the messages to maintain the order of conversation
        chat_history = [{"name": "AI" if msg.author == client.user \
                            else "Human", "content": msg.content} \
                            for msg in reversed(history[1:])]

        print(f"Chat history: {chat_history}")

        if len(clean_content) > 10:
            # Forward the message content to your Flask app
            flask_app_url = f'{FLASKURL}/discord/edmonbrain/message'
            print(f'Calling {flask_app_url}')
            payload = {
                'content': clean_content,
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
                            metadata_source = source.get('metadata')
                            source_message = f"*source*: {metadata_source.get('source')}"
                            await chunk_send(new_thread, source_message)

                        # Edit the thinking message to show the reply
                        await thinking_message.edit(content=reply_content)

                        # Check if the message was sent in a thread or a private message
                        if isinstance(new_thread, discord.Thread):
                            await new_thread.send(f"Reply to {bot_mention} within this thread to continue. Use !savethread to save thread to database")
                        elif isinstance(new_thread, discord.DMChannel):
                            # Its a DM
                            await new_thread.send(f"Use !savethread to save private chat history to database")
                        else:
                            print(f"I couldn't work out the channel type: {new_thread}")
                    else:
                        # Edit the thinking message to show an error
                        await thinking_message.edit(content="Error in processing message.")
        else:
            print(f"Got a little message not worth sending: {clean_content}")
            await thinking_message.edit(content="Your reply is too small to think too long about")

    if message.attachments:

        # Send a thinking message
        thinking_message2 = await new_thread.send("Uploading file(s)..")

        # Forward the attachments to Flask app
        flask_app_url = f'{FLASKURL}/discord/edmonbrain/files'
        print(f'Calling {flask_app_url}')
        payload = {
            'attachments': [{'url': attachment.url, 'filename': attachment.filename} for attachment in message.attachments],
            'content': clean_content,
            'chat_history': chat_history
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(flask_app_url, json=payload) as response:
                print(f'file response.status: {response.status}')
                if response.status == 200:
                    response_data = await response.json()
                    print(f'response_data: {response_data}')
                    summaries = response_data.get('summaries', [])
                    for summary in summaries:
                        await chunk_send(new_thread, summary)
                    await thinking_message2.edit(content="Uploaded file(s)")
                else:
                    # Edit the thinking message to show an error
                    await thinking_message2.edit(content="Error in processing file(s).")

client.run(TOKEN)
