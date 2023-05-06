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
# https://console.cloud.google.com/bigquery?sq=555344851243:829a80edb74a48bcb221b30635ca8c7a