CREATE FUNCTION match_documents_{vector_name}(query_embedding vector(1536), match_count int)
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
        1 -({vector_name}.embedding <=> query_embedding) AS similarity
    FROM
        {vector_name}
    ORDER BY
        {vector_name}.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;