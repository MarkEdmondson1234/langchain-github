# QnA

This code is for loading in files and then being able to ask questions about them.

## QnA over a directory

This utility imports files from a directory into a Chroma vector store, which is then used to provide context to the LLM for when you ask questions about that directory.

Configure location for vector store and make it executable:

```
echo 'export CHROMA_DB_PATH=/Users/mark/dev/ml/chat_history/' >> ~/.zshenv
source ~/.zshenv
chmod u+x qna/read_repo.py
```

At the top of the `qna/read_repo.py` file is the python installation it will use.  This is currently set to my local Python directory environment, created by venv above in `./env/bin/python`. Change it so it mirrors yours.

```
#!/Users/mark/dev/ml/langchain/read_github/langchain_github/env/bin/python
# change above to the location of your local Python venv installation
```

You should then be able to use it like this.  If not use ChatGPT like I did to debug Python executable environments etc etc.

```
> ./qna/read_repo.py -h
usage: read_repo.py [-h] [--reindex] [--ext EXT] [--ignore IGNORE] [--resummarise] repo

Chat with a GitHub repository

positional arguments:
  repo             The GitHub repository on local disk

optional arguments:
  -h, --help       show this help message and exit
  --reindex        Whether to re-index the doc database that supply context to the Q&A (default: False)
  --ext EXT        Comma separated list of file extensions to include. Defaults to '.md,.py' (default: None)
  --ignore IGNORE  Directory to ignore file imports from. Defaults to 'env/' (default: None)
  --resummarise    Recreate the code.md files describing the code (default: False)
```

### installation so it runs anywhere (MacOS)

This is helpful so you can browse to other repositories and use the script there more easily.

Make the `read_repo_wrapper.sh` script executable:

```
> chmod +x /path/to/qna/read_repo_wrapper.sh
```

This wrapper script sets the working directory for the `qna/read_repo.py` script so you can sym link it to your local path.

Make sure to replace /path/to with the actual path to the read_repo_wrapper.sh script.

Create a symlink to the read_repo_wrapper.sh script in /usr/local/bin:

```
> sudo ln -s /path/to/qna/read_repo_wrapper.sh /usr/local/bin/read_repo
```

This makes you able to just use `read_repo` instead of `./qna/read_repo.py`

Make sure to replace /path/to with the actual path to the read_repo_wrapper.sh script.

Now the user can run the read_repo command from anywhere on their Mac:

```
> read_repo -h
usage: read_repo.py [-h] [--reindex] [--ext EXT] [--ignore IGNORE] [--resummarise] repo

Chat with a GitHub repository

positional arguments:
  repo             The GitHub repository on local disk

optional arguments:
  -h, --help       show this help message and exit
  --reindex        Whether to re-index the doc database that supply context to the Q&A (default: False)
  --ext EXT        Comma separated list of file extensions to include. Defaults to '.md,.py' (default: None)
  --ignore IGNORE  Directory to ignore file imports from. Defaults to 'env/' (default: None)
  --resummarise    Recreate the code.md files describing the code (default: False)
```


### Running the script

On first run it will create the database.  To make the QnA more useful, it will also generate .md files for any scripts you have indicated you want to read (e.g. script.py will have script.md generated in the same folder).  You can see examples in this repository.

If using this to QnA over a public repository, you may wish to change to a private local branch so you don't pollute the repo with lots of .md files. 

You can renew the database by using the --reindex option, and recreate the summaries with the --resummarise option.

```
# Read this directory ($PWD)
read_repo $PWD --ext='.md,.md,.yaml' --reindex --resummarise
```

(You may need to replace `read_repo` with `./qna/read_repo.py` if you did not add it to your path as described above)

It lets you ask questions in the command line:

```
Loading Chroma DB from ./chroma/langchain-github.
Using embedded DuckDB with persistence: data will be stored in: ./chroma/langchain-github

Ask a question. CTRL + C to quit.
```

You can specify what file extensions you want to include in the database, and which folders to ignore.  The default ignores the `env/` folder, typically as its used for `venv`

```
# make a new database to include all .md/.py/.txt files
read_repo $PWD --reindex --ext='.md,.py,.txt'
Creating Chroma DB at ./chroma/langchain-github ...
Ignoring /Users/mark/dev/ml/langchain/read_github/langchain-github/env
Reading .md files
Read 1 and ignored 9 .md files.
Reading .py files
Read 16 and ignored 11130 .py files.
Reading .txt files
Read 9 and ignored 170 .txt files.
Read all files
Using embedded DuckDB with persistence: data will be stored in: ./chroma/langchain-github

Ask a question. CTRL + C to quit.
What is this repo about?

Answer:
I don't know.
== Document sources:
 - README.md
 - qna/read_repo.py
 - README.md
 - qna/read_repo.py


Ask a question. CTRL + C to quit.
summarise this readme

Answer: This utility imports files from a directory into a Chroma vector store, which is then used to provide context to the LLM for when you ask questions about that directory. You can specify what file extensions you want to include and what directories to ignore when importing documents.
== Document sources:
 - argparse_example.py
 - README.md
 - qna/read_repo.py
 - qna/read_repo.py
```



## LLM Generated Description

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

## Example with the langchain repository

Here is an example with the langchain repository https://github.com/hwchase17/langchain which contains lots of files that I wish to build an index for.  Note that this will also send the summaries to the chat history on BigQuery.

1. Fork the repository on GitHub e.g. https://github.com/MarkEdmondson1234/langchain
1. Clone the repo and create a new fork "summaries"
1. In your shell browse to the Python package directory e.g. `cd /Users/mark/dev/forks/langchain/langchain`
1. Issue the command both summarise all the files `--resummarise` (this sends paid for calls to OpenAI) and put those summarises in the Chroma vectorstore (`--reindex`) so they are available for context in your QnA.

```
read_repo $PWD --ext='.md,.py,.yaml' --reindex --resummarise
```

This step will take a while as it sends each file's data to OpenAI requesting a summary and writing files.  

If you need to stop half way through, the existing file.md files will still be available as written to disk.  You can pick up where you left off by excluding `--resummarise` to keep the existing files.  If you want any individual files to be regenerated, delete the `file.md` you want to redo.

```
read_repo $PWD --ext='.md,.py,.yaml' --reindex
```

Once done, you can just do a QnA over the summaries and code via:

```
read_repo $PWD
```