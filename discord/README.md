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


New set up