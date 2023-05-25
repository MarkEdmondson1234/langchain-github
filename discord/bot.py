import os
import discord
import aiohttp
import json
from dotenv import load_dotenv
import shlex

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN', None)  # Get your bot token from the .env file
FLASKURL = os.getenv('FLASK_URL', None)

def load_config(filename):
    with open(filename, 'r') as f:
        config = json.load(f)
    return config

# Load the config file at the start of your program
config = load_config('config.json')

def select_vectorname(message):
    if message.guild is not None:  
        server_name = message.guild.name
        if server_name in config:
            vector_name = config[server_name]
            print(f'Guild: {server_name} - vector_name: {vector_name}')
            return config[server_name]

        raise ValueError(f"Could not find a configured vector for server_name: {server_name}")
    return None



if TOKEN is None or FLASKURL is None:
    raise ValueError("Must set env vars DISCORD_TOKEN, FLASK_URL in .env")

intents = discord.Intents.default()
intents.messages = True
intents.dm_messages = True  # Enable DM messages

client = discord.Client(intents=intents)

async def chunk_send(channel, message):
    chunks = [message[i:i+1500] for i in range(0, len(message), 1500)]
    for chunk in chunks:
        await channel.send(chunk)

async def make_chat_history(new_thread, bot_mention, client_user):
    history = []
    async for msg in new_thread.history(limit=30):
        if msg.content.startswith(f"*Reply to {bot_mention}"):
            continue
        if msg.content.startswith("*Use !savethread"):
            continue
        if msg.content.startswith("**source**:"):
            continue
        if msg.content.startswith("**url**:"):
            continue
        history.append(msg)

    # Reverse the messages to maintain the order of conversation
    chat_history = []
    for msg in reversed(history[1:]):
        author = "AI" if msg.author == client_user else "Human"
        content = msg.content
        embeds = [embed.to_dict() for embed in msg.embeds]
        chat_history.append({"name": author, "content": content, "embeds": embeds})


    return chat_history

async def make_new_thread(message, clean_content):
    # Check if the message was sent in a thread or a private message
    if isinstance(message.channel, (discord.Thread, discord.DMChannel)):
        new_thread = message.channel
    else:
        if len(clean_content) < 5:
            thread_name = "Baaa--zzz"
        else:
            thread_name = f"Baa-zzz - {clean_content[:40]}"
        # If it's not a thread, create a new one
        new_thread = await message.channel.create_thread(
            name=thread_name, 
            message=message)

    return new_thread

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # If the bot isn't mentioned and it's not a DM, return
    if not isinstance(message.channel, discord.DMChannel)  \
       and client.user not in message.mentions:
        return

    bot_mention = client.user.mention

    clean_content = message.content.replace(bot_mention, '')

    new_thread = await make_new_thread(message, clean_content)

    chat_history = await make_chat_history(new_thread, bot_mention, client.user)

    if message.content:
        print(f'Got the message: {message.content}')

        debug=False
        if message.content.startswith("!debug"):
            debug = True

        clean_content = message.content.replace(bot_mention, '')

        try:
            VECTORNAME = select_vectorname(message)
        except ValueError as e:
            print(e)
            return  # exit the event handler

        if VECTORNAME == None:
            # debug mode for me
            print(f'DM from {message.author}')
            if str(message.author) == "MarkeD#2972":
                VECTORNAME="edmonbrain"
                debug=True
                words = shlex.split(str(message.content))
                print(words)
                if words[0] == "!vectorname":
                    VECTORNAME = words[1]
                    await chunk_send(message.channel, f"vectorname={VECTORNAME}")
                    clean_content = words[2]
                else:
                    await chunk_send(message.channel, "Hello Master. Use !vectorname <vector_name> 'clean content' to debug")
            else:
                return

        # Send a thinking message
        thinking_message = await new_thread.send("Thinking...")

        if len(clean_content) > 10:
            # Forward the message content to your Flask app
            flask_app_url = f'{FLASKURL}/discord/{VECTORNAME}/message'
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
                        #print(f'response_data: {response_data}')

                        source_docs = response_data.get('source_documents', [])
                        reply_content = response_data.get('result')  # Get the 'result' field from the JSON

                        # dedupe source docs
                        seen = set()
                        unique_source_docs = []

                        for source in source_docs:
                            metadata_str = json.dumps(source.get('metadata'), sort_keys=True)
                            if metadata_str not in seen:
                                unique_source_docs.append(source)
                                seen.add(metadata_str)

                        for source in unique_source_docs:
                            metadata_source = source.get('metadata')
                            #if debug:
                            source_message = f"**source**: {metadata_source.get('source')}"
                            await chunk_send(new_thread, source_message)
                            source_url = metadata_source.get('url', None)
                            if source_url is not None:
                                url_message = f"**url**: {source_url}"
                                await chunk_send(new_thread, url_message)


                        # Edit the thinking message to show the reply
                        await thinking_message.edit(content=reply_content)

                        # Check if the message was sent in a thread or a private message
                        if isinstance(new_thread, discord.Thread):
                            await new_thread.send(f"*Reply to {bot_mention} within this thread to continue. Use `!savethread` to save thread to database, or `!saveurl` to save content at a URL*")
                        elif isinstance(new_thread, discord.DMChannel):
                            # Its a DM
                            await new_thread.send(f"*Use `!savethread` to save private chat history to database, or `!saveurl` to save content at a URL*")
                        else:
                            print(f"I couldn't work out the channel type: {new_thread}")
                    else:
                        # Edit the thinking message to show an error
                        await thinking_message.edit(content="Error in processing message.")
        else:
            print(f"Got a little message not worth sending: {clean_content}")
            await thinking_message.edit(content=f"Your reply is too small to think too long about: {clean_content}")

    if message.attachments:

        max_file_size = 10 * 1024 * 1024  # 10 MB
        for attachment in message.attachments:
            if attachment.size > max_file_size:
                await thinking_message.edit("Sorry, a file is too large to upload via Discord, please use another method such as the bucket.  Uploaded files need to be smaller than 10MB each.")
                return

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
