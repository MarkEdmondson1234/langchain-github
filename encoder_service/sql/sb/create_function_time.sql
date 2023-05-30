CREATE OR REPLACE FUNCTION calculate_age_in_days(objectId text, eventTime text)
    RETURNS float
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN EXTRACT(EPOCH FROM NOW() - TO_TIMESTAMP(COALESCE(SUBSTRING(eventTime FROM 1 FOR 19), SUBSTRING(objectId FROM 14 FOR 13)), 'YYYY-MM-DD"T"HH24:MI:SS')) / (60*60*24);
END;
$$;

CREATE OR REPLACE FUNCTION match_documents_{vector_name}(query_embedding vector(1536), match_count int)
    RETURNS TABLE(
        id bigint,
        content text,
        metadata jsonb,
        embedding vector(1536),
        similarity float)
    LANGUAGE plpgsql
    AS $$
    # variable_conflict use_column
BEGIN
    RETURN query
    WITH latest_documents AS (
        SELECT *
        FROM {vector_name}
        WHERE (metadata->>'objectId', TO_TIMESTAMP(COALESCE(SUBSTRING(metadata->>'eventTime' FROM 1 FOR 19), SUBSTRING(metadata->>'objectId' FROM 14 FOR 13)), 'YYYY-MM-DD"T"HH24:MI:SS')) IN (
            SELECT metadata->>'objectId', MAX(TO_TIMESTAMP(COALESCE(SUBSTRING(metadata->>'eventTime' FROM 1 FOR 19), SUBSTRING(metadata->>'objectId' FROM 14 FOR 13)), 'YYYY-MM-DD"T"HH24:MI:SS'))
            FROM {vector_name}
            GROUP BY metadata->>'objectId'
        )
    )
    SELECT
        id,
        content,
        metadata,
        embedding,
        1 -(latest_documents.embedding <=> query_embedding) - calculate_age_in_days(metadata->>'objectId', metadata->>'eventTime') AS similarity
    FROM
        latest_documents
    ORDER BY
        2 * (1 -(latest_documents.embedding <=> query_embedding)) - calculate_age_in_days(metadata->>'objectId', metadata->>'eventTime') DESC,
        TO_TIMESTAMP(COALESCE(SUBSTRING(metadata->>'eventTime' FROM 1 FOR 19), SUBSTRING(metadata->>'objectId' FROM 14 FOR 13)), 'YYYY-MM-DD"T"HH24:MI:SS') DESC
    LIMIT match_count;
END;
$$;
