CREATE MATERIALIZED VIEW  langchain.pubsub_staging AS (
SELECT 
    JSON_VALUE(SAFE.PARSE_JSON(data), "$.content") as content,
    JSON_VALUE(SAFE.PARSE_JSON(data), "$.role") as role,
    JSON_VALUE(SAFE.PARSE_JSON(data), "$.timestamp") as created_timestamp,
    JSON_VALUE(SAFE.PARSE_JSON(data), "$.additional_kwargs") as additional_kwargs,
    JSON_QUERY(SAFE.PARSE_JSON(data), "$.metadata") as metadata,
    JSON_VALUE(SAFE.PARSE_JSON(data), "$.system_string") as system_string,
    SAFE.PARSE_JSON(data) as data_json,
    subscription_name,
    message_id,
    publish_time,
    attributes
  FROM  `langchain.pubsub_raw`
  WHERE DATE(publish_time) > "2023-04-13"
  AND SAFE.PARSE_JSON(data) IS NOT NULL
  )