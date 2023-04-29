history = TimedChatMessageHistory("my_memory")
history.add_user_message("Hello!")
history.add_ai_message("Hi there!")
history.add_user_message("How are you?")
history.add_ai_message("I'm doing well, thanks for asking.")
history.clear()
history.load_chat_history()


"""
This code defines a class `TimedChatMessageHistory` that extends `BaseChatMessageHistory` and adds timestamps to messages. It also defines several helper functions for working with `TimedChatMessage` objects, such as `timed_messages_to_dict()` and `timed_messages_from_dict()`. 

The `TimedChatMessageHistory` class has several methods for adding messages to the chat history, clearing the chat history, and loading the chat history from a file. The `timed_messages_to_dict()` function converts a list of `TimedChatMessage` objects to a list of dictionaries, and the `timed_messages_from_dict()` function does the reverse.

Here's an example of how you might use this code:


"""
