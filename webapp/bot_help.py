import os
from encoder_service import publish_to_pubsub_embed

def app_to_store(safe_file_name, vector_name):
    gs_file = publish_to_pubsub_embed.add_file_to_gcs(safe_file_name, vector_name)
    publish_to_pubsub_embed.publish_text(gs_file, vector_name)
    
def handle_files(uploaded_files, temp_dir, vector_name):
    bot_output = []
    if uploaded_files:
        for file in uploaded_files:
            # Save the file temporarily
            safe_filepath = os.path.join(temp_dir, file.filename)
            file.save(safe_filepath)

            app_to_store(safe_filepath, vector_name)
            bot_output.append(f"{file.filename} sent to {vector_name}")

    return bot_output

def generate_output(bot_output):
    if bot_output['source_documents'] is not None:
        source_documents = []
        for doc in bot_output['source_documents']:
            metadata = doc.metadata
            filtered_metadata = {}
            if metadata.get("source", None) is not None:
                filtered_metadata["source"] = metadata["source"]
            if metadata.get("type", None) is not None:
                filtered_metadata["type"] = metadata["type"]
            source_doc = {
                'page_content': doc.page_content,
                'metadata': filtered_metadata
            }
            source_documents.append(source_doc)

    return {
        'result': bot_output['answer'],
        'source_documents': source_documents
    }

def extract_chat_history(chat_history=None):
    
    if chat_history:
        # Separate the messages into human and AI messages
        human_messages = [message["content"] for message in chat_history if message["name"] == "Human"]
        ai_messages = [message["content"] for message in chat_history if message["name"] == "AI"]
        # Pair up the human and AI messages into tuples
        paired_messages = list(zip(human_messages, ai_messages))
    else:
        print("No chat history found")
        paired_messages = None

    return paired_messages