# UX for EdmonBrain

This is an exploration on how to interact with the LLM tools in this repo

## Deploy to Cloud Run

### Add secrets to Secret Manager

* OPENAI_API_KEY

### IAM

Use default service account, or better is use a dedicated service account with these permissions

e.g. `your-app@your-project.iam.gserviceaccount.com`

* Pub Sub Editor
* Storage Admin

### Run Cloud Build

Run from the root directory of this repository

```
gcloud builds submit --config cloudbuild.yaml . \
  --substitutions=_IMAGE_NAME=edmonbrain,_SERVICE_NAME=edmonbrain-app,_REGION=europe-west3,_GCS_BUCKET=bucket-to-store-vectorstore,_SERVICE_ACCOUNT=your-service-account@your-project.iam.gserviceaccount.com
```

Or preferably set up a Cloud Build Trigger for each git commit


## WebApp

Can be used to configure the vectorstore index

Run locally:

```
./env/bin/python3 ./webapp/app.py   
```

Give its service account running the Cloud Run Cloud Storage read/write permissions if you supply the _GCS_BUCKET

## Discord bot

Can accept inputs, outputs, proviides chat history and can upload limited files

Register a new bot with Discord.com

1. Make a new Discord application: https://discord.com/developers/applications
1. Create a new Bot under that application
1. Generate DISCORD_TOKEN to put in the bot.py script via .env
1. Go to OAuth2 > URL Generator to create an invite link and save it somewhere safe
1. Click on invite link and add the bot to your own Discord server

Need a seperate Discord bot hosting service with a bot that will call the Cloud Run URL.

I deploy mine from this repo https://github.com/MarkEdmondson1234/discord-bot

1. Upload bot.py, requirements.txt and .env to the Discord bot server
1. Verify bot server is running

I couldn't make it work permissions with to read every message in a channel, but it does work for direct messages to the bot, which is probably best anyway.

![](img/discord-llm-bit.png)

### Routing

1. User adds file and it is sent to /discord/<vector_name>/files
2. /discord/<vector_name>/files sends each file to encoder_service/publish_to_pubsub_embed.add_file_to_gcs and generates gs:// filename
3. /discord/<vector_name>/files then sends filename to PubSub topic `app_to_pubsub_<vector_name>` via publish_text()
4. PubSub subscription `pubsub_to_app_chunk_<edmonbrain>` pushes filename to `/pubsub_to_store/<vector_name>`
5. `/pubsub_to_store/<vector_name>` chunks up data and sends to PubSub topic "embed_chunk"
6. "embed_chunk" sends data to sub pubsub_to_store_edmonbrain and then to /pubsub_chunk_to_store/edmonbrain which sends each chunk to Supabase

## Slackbot

Can only accept inputs and outputs

```
echo 'export SLACK_BOT_TOKEN=XXXX' >> ~/.zshenv
source ~/.zshenv
```