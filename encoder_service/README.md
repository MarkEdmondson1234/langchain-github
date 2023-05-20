# Supabase setup

In addition to the normal setup instructions, make sure the SQL functions are also referring to the correct database.  So you need one Supacebase URL per bot, basically.

```sql
CREATE OR REPLACE FUNCTION match_documents(query_embedding vector(1536), match_count int)
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
               1 -(edmonbrain.embedding <=> query_embedding) AS similarity
           FROM
               edmonbrain
           ORDER BY
               edmonbrain.embedding <=> query_embedding
           LIMIT match_count;
       END;
       $$;
```