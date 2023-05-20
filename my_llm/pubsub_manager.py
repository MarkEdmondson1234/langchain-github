from google.cloud import pubsub_v1
from google.api_core.exceptions import NotFound
from google.auth import default

import json
import os
import logging

logging.basicConfig(level=logging.INFO)

class PubSubManager:
    """
    Creates a new PubSub topic is necessary and sends pubsub messages to it
    """
    def __init__(self, memory_namespace: str, pubsub_topic: str=None, project_id: str=None, verbose:bool=False):
        self.project_id = project_id
        self.pubsub_topic = pubsub_topic
        self.publisher = None
        self.verbose = verbose
        self.memory_namespace = memory_namespace

        # Get the project ID from the default Google Cloud settings or the environment variable
        _, project_id = default()
        self.project_id = project_id or os.environ.get('GOOGLE_CLOUD_PROJECT')

        if self.project_id:
            logging.info(f"Project ID: {self.project_id}")
            # Create the Pub/Sub topic based on the project ID and memory_namespace
            self.publisher = pubsub_v1.PublisherClient()
            self.pubsub_topic = f"projects/{self.project_id}/topics/{pubsub_topic}" or \
                                f"projects/{self.project_id}/topics/chat-messages-{memory_namespace}"
            self._create_pubsub_topic_if_not_exists()

        else:
            # No project ID is available
            print("GOOGLE_CLOUD_PROJECT not set and gcloud default settings not available")

    def _create_pubsub_topic_if_not_exists(self):
        """Creates the Pub/Sub topic if it doesn't already exist."""
        try:
            # Check if the topic exists
            self.publisher.get_topic(request={"topic": self.pubsub_topic})
        except NotFound:
            # If the topic does not exist, create it
            self.publisher.create_topic(request={"name": self.pubsub_topic})
            logging.info(f"Created Pub/Sub topic: {self.pubsub_topic}")
            if self.verbose:
                print(f"Created Pub/Sub topic: {self.pubsub_topic}")

    @staticmethod
    def _callback(future):
        try:
            message_id = future.result()
            logging.info(f"Published message with ID: {message_id}")
        except Exception as e:
            logging.error(f"Failed to publish message: {e}")

    def publish_message(self, message:str, verbose=False):
        """Publishes the given data to Google Pub/Sub."""

        if verbose or self.verbose:
            verbose = True
        
        if isinstance(message, dict):
                message = json.dumps(message)
        
        if self.publisher and self.pubsub_topic:
            message_bytes = message.encode('utf-8')
            attr = {"namespace": str(self.memory_namespace)}
            future = self.publisher.publish(self.pubsub_topic, message_bytes, attrs=json.dumps(attr))
            future.add_done_callback(self._callback)

