import psycopg2
import logging
import os

def setup_supabase(vector_name):

    params = {'vector_name': vector_name}

    try:
        execute_sql_from_file("sql/sb/setup.py", params)
    except Exception as e:
        logging.info("setup ok")
    
    try:
        execute_sql_from_file("sql/sb/create_table.sql", params)
    except Exception as e:
        logging.info("table create ok")
    
    try:
        execute_sql_from_file("sql/sb/create_function.sql", params)
    except Exception as e:
        logging.info("create function ok")
    
    return True


def execute_sql_from_file(filename, params):
    return execute_supabase_from_file(filename, params)

def execute_supabase_from_file(filepath, params):

     # Get the directory of this Python script
    dir_path = os.path.dirname(os.path.realpath(__file__))
    # Build the full filepath by joining the directory with the filename
    filepath = os.path.join(dir_path, filepath)

    # read the SQL file
    with open(filepath, 'r') as file:
        sql = file.read()

    # substitute placeholders in the SQL
    sql = sql.format(**params)
    connection_string = os.getenv('DB_CONNECTION_STRING', None)
    if connection_string is None:
        raise ValueError("No connection string")

    try:
        connection = psycopg2.connect(connection_string)
        cursor = connection.cursor()

        # execute the SQL
        cursor.execute(sql)

        # commit the transaction to save changes to the database
        connection.commit()

        logging.info(f"Successfully executed SQL script from {filepath}")

    except (Exception, psycopg2.Error) as error:
        logging.error("Error while connecting to PostgreSQL", exc_info=True)

    finally:
        if (connection):
            cursor.close()
            connection.close()
            logging.info("PostgreSQL connection is closed")
