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

1. Create a config file that will look up your Discord server name and determine which brain to use:

```
{
	"Mark Edmondson": "edmonbrain",
	"Another Discord Server": "blah.com"
}
```

1. Upload bot.py, config.yaml, requirements.txt and .env to the Discord bot server
1. Verify bot server is running

Discord bot will need to be mentioned via @ElectricSheep to get data sent to the bot

![](img/discord-llm-bit.png)

### 

### Routing

1. Create a dead letter topic/sub that will write failed messages to BigQuery.  This prevents the message trying forever and running up bills.  Assign this dead letter topic to all PubSub subscriptions made below. 

1. the first document attempted to load will create a pubsub topic `app_to_pubsub_<vector_name>` or make it yourself.
1. Make a subscription for above topic called `pubsub_to_store_<vector_name>` that pushes data to https://your-cloudrun-app.a.run.app/pubsub_to_store/<vector_name>
1. That will make a topic called `embed_chunk_<vector_name>` or make it yourself.
1. Create a subscription to topic `embed_chunk_<vector_name>` called `pubsub_chunk_to_store_<vector_name>` that pushes data to https://your-cloudrun-app.a.run.app/pubsub_chunk_to_store/<vector_name>

/discord/<vector_name>/files --> pubsub_topic="app_to_pubsub_<vector_name>" --> pubsub_sub="pubsub_to_store_<vector_name>  -->
/pubsub_to_store/<vector_name> --> pubsub_topic="embed_chunk_<vector_name>" --> pubsub_sub="pubsub_chunk_to_store_<vector_name> -->
/pubsub_chunk_to_store/<vector_name> --> supabase db_table=<vector_name>

## Cloud Storage files to embed vector database

Make a PubSub topic fire for each file added to a cloud storage bucket and aim it at `app_to_pubsub_<vector_name>`

e.g.

```
gcloud storage buckets notifications create gs://devoteam-mark-langchain-loader --topic=app_to_pubsub_<vector_name>
```

Now every file added to the cloud storage bucket will trigger a pipeline of loading it as a document, splitting it up into chunks, embedding them and sending to the vector database.

## Slackbot

Can only accept inputs and outputs

```
echo 'export SLACK_BOT_TOKEN=XXXX' >> ~/.zshenv
source ~/.zshenv
```