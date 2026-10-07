import os

import psycopg
from psycopg.rows import dict_row


def get_connection():
    # Read the database address and credentials.
    database_url = os.environ["DATABASE_URL"]

    # Create a connection and return it to the calling function.
    return psycopg.connect(
        database_url,
        row_factory=dict_row,
    )