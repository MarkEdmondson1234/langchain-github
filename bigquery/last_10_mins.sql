SELECT
  SAFE.PARSE_JSON(data) as data_json
FROM
  `langchain.pubsub_raw`
WHERE
  publish_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE) AND data != "null"