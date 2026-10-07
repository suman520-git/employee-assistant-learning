import os

import psycopg
from psycopg.rows import dict_row


# Read the connection details from the environment variable.
database_url = os.environ["DATABASE_URL"]

# Connect to PostgreSQL.
with psycopg.connect(database_url, row_factory=dict_row) as connection:

    # Send our SQL query to PostgreSQL.
    cursor = connection.execute(
        "SELECT id, name, department_id FROM employees ORDER BY id"
    )

    # Read all returned rows into a Python list.
    employees = cursor.fetchall()

    # Display the result.
    print(employees)