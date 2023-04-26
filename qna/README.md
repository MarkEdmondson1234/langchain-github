# QnA

This script is a command-line tool that enables the user to ask questions about a GitHub repository and get answers based on the content of the repository.

Here's what the different functions in the script do:

    get_repo_docs: Given a path to a local repository and a list of file extensions, this function finds all files in the repository that have one of the specified extensions, reads the content of the files, and yields a Document object for each file. The Document object represents a page of content with associated metadata.
    get_source_chunks: This function uses get_repo_docs to get all the documents in a repository, and then splits each document into chunks of a specified size (1024 characters). It returns a list of Document objects, each representing a chunk of source code.
    main: This is the main function of the script. It does the following:
        Parses command-line arguments using argparse.
        Calls get_source_chunks to get all the source code chunks in the specified repository.
        If a Chroma vector store (a type of database used for similarity matching) does not exist for the repository, or if the --reindex flag is specified, it creates a new Chroma vector store using the source code chunks and saves it to disk.
        If a Chroma vector store exists, it loads it from disk.
        Creates a retrieval-based question answering system using the loaded Chroma vector store and an OpenAI language model.
        Enters a loop where it prompts the user for a question, uses the QA system to find an answer based on the repository content, and prints the answer along with the source document(s) that were used to find the answer.

Overall, the script combines several natural language processing techniques to enable users to interact with a GitHub repository using natural language.