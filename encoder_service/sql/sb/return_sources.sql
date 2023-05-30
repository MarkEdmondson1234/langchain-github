SELECT metadata->>'source' AS source
FROM {vector_name}
WHERE TO_TIMESTAMP(COALESCE(SUBSTRING(metadata->>'eventTime' FROM 1 FOR 19), SUBSTRING(metadata->>'objectId' FROM 14 FOR 13)), 'YYYY-MM-DD"T"HH24:MI:SS') > NOW() - INTERVAL '{time_period}';
