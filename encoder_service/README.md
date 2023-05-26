# Supabase setup

Requires `DB_CONNECTION_STRING` environment variable got from the database (Supabase)

Run the script if running locally:

```
./env/bin/python3 ./encoder_service/database.py test_db2
```

Or when sending a PubSub message for the first time to a new vector_space, it will run the `./encoder_service/database.py` script when making the first pubsub subscription to the topic. 
