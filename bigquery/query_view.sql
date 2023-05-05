SELECT
  content,
  role,
  created_timestamp,
  additional_kwargs,
  metadata,
  data_json,
  subscription_name,
  message_id,
  publish_time,
  attributes
FROM
  langchain.pubsub_staging
WHERE
  content LIKE '%keyword%';
