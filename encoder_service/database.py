import psycopg2
from psycopg2.extensions import adapt
import logging
import os

def setup_database(vector_name:str, verbose:bool=False):
    setup_supabase(vector_name, verbose)

def setup_supabase(vector_name:str, verbose:bool=False):

    hello = f"Setting up database: {vector_name}"
    logging.info(hello)
    if verbose:
        print(hello)
    
    params = {'vector_name': vector_name}

    execute_sql_from_file("sql/sb/setup.sql", params)
    execute_sql_from_file("sql/sb/create_table.sql", params)
    execute_sql_from_file("sql/sb/create_function.sql", params)

    if verbose: print("Ran all setup SQL statements")
    
    return True

def return_sources_last24(vector_name:str):
    params = {'vector_name': vector_name, 'time_period':'1 day'}
    return execute_sql_from_file("sql/sb/return_sources.sql", params, return_rows=True)

def delete_row_from_source(source: str, vector_name:str):
    # adapt the user input and decode from bytes to string to protect against sql injection
    source = adapt(source).getquoted().decode()
    sql_params = {'source_delete': source}
    sql = f"""
        DELETE FROM {vector_name}
        WHERE metadata->>'source' = %(source_delete)s
    """

    do_sql(sql, sql_params=sql_params)

def do_sql(sql, sql_params=None, return_rows=False):
    rows = []
    connection_string = os.getenv('DB_CONNECTION_STRING', None)
    if connection_string is None:
        raise ValueError("No connection string")

    try:
        connection = psycopg2.connect(connection_string)
        cursor = connection.cursor()

        # execute the SQL - raise the error if already found
        cursor.execute(sql, sql_params)

        # commit the transaction to save changes to the database
        connection.commit()

        if return_rows:
            rows = cursor.fetchall()
    
    except (psycopg2.errors.DuplicateObject, 
            psycopg2.errors.DuplicateTable, 
            psycopg2.errors.DuplicateFunction) as e:
        logging.info(str(e))
        print(str(e))

    except (Exception, psycopg2.Error) as error:
        logging.error("Error while connecting to PostgreSQL", exc_info=True)

    finally:
        if (connection):
            cursor.close()
            connection.close()
            logging.info("PostgreSQL connection is closed")
    
    if rows:
        return rows
    
    return None


def execute_sql_from_file(filename, params, return_rows=False):
    return execute_supabase_from_file(filename, params, return_rows)

def execute_supabase_from_file(filepath, params, return_rows=False):

     # Get the directory of this Python script
    dir_path = os.path.dirname(os.path.realpath(__file__))
    # Build the full filepath by joining the directory with the filename
    filepath = os.path.join(dir_path, filepath)

    # read the SQL file
    with open(filepath, 'r') as file:
        sql = file.read()

    # substitute placeholders in the SQL
    sql = sql.format(**params)
    rows = do_sql(sql, return_rows=return_rows)
    
    if return_rows:
        if rows is None: return None
        return rows
    
    return True

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Setup a supabase database",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("vectorname", help="The namespace for Supabase vectorstore")

    args = parser.parse_args()
    config = vars(args)

    vector_name = config.get('vectorname', None)
    if vector_name is None:
        raise ValueError("Must provide a vectorname")
    
    setup_supabase(vector_name, verbose=True)
