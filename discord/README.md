# Discord bot

A bot that can be used within Discord.

## Setup

1. Add the bot to the Discord server via this link:

1. Add bot to the channels you want it to use within the server
1. Setup the Supabase tables and functions - example below for `fnd`

```sql
-- Enable the pgvector extension to work with embedding vectors
       --create extension vector;

       -- Create a table to store your documents
       create table fnd (
       id bigserial primary key,
       content text, -- corresponds to Document.pageContent
       metadata jsonb, -- corresponds to Document.metadata
       embedding vector(1536) -- 1536 works for OpenAI embeddings, change if needed
       );

       CREATE FUNCTION match_documents_fnd(query_embedding vector(1536), match_count int)
           RETURNS TABLE(
               id bigint,
               content text,
               metadata jsonb,
               -- we return matched vectors to enable maximal marginal relevance searches
               embedding vector(1536),
               similarity float)
           LANGUAGE plpgsql
           AS $$
           # variable_conflict use_column
       BEGIN
           RETURN query
           SELECT
               id,
               content,
               metadata,
               embedding,
               1 -(fnd.embedding <=> query_embedding) AS similarity
           FROM
               fnd
           ORDER BY
               fnd.embedding <=> query_embedding
           LIMIT match_count;
       END;
       $$;
```

1. Add to config file:

```json
{
	"Mark Edmondson": "edmonbrain",
	"Illys Shield": "fnd"
}
```

1. Create a dead letter topic/sub that will write failed messages to BigQuery.  This prevents the message trying forever and running up bills.  Assign this dead letter topic to all PubSub instances below. 

1. the first document attempted to load will create a pubsub topic `app_to_pubsub_fnd` or make it yourself.
1. Make a subscription called `pubsub_to_store_fnd` that pushes data to https://your-cloudrun-app.a.run.app/pubsub_to_store/fnd
1. That will make a topic called `embed_chunk_fnd` or make it yourself.
1. Create a subscription to `embed_chunk_fnd` called `pubsub_chunk_to_store_fnd` that pushes data to https://edmonbrain-app-xsww4stuxq-ey.a.run.app/pubsub_chunk_to_store/fnd

/discord/<vector_name>/files --> pubsub_topic="app_to_pubsub_<vector_name>" --> pubsub_sub="pubsub_to_store_<vector_name>  -->
/pubsub_to_store/<vector_name> --> pubsub_topic="embed_chunk_<vector_name>" --> pubsub_sub="pubsub_chunk_to_store_<vector_name> -->
/pubsub_chunk_to_store/<vector_name> --> supabase db_table=<vector_name>