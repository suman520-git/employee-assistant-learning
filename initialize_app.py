import os
import time

from qdrant_client import models

from database import get_connection
from graph_store import driver
from graph_sync import sync_all_graph
from vector_store import client, COLLECTION_NAME, index_document


def initialize_app():
    # Containers can be running before their databases are ready.
    for attempt in range(30):
        try:
            client.get_collections()
            driver.verify_connectivity()
            break
        except Exception:
            if attempt == 29:
                raise

            print("Waiting for Qdrant and Neo4j...", flush=True)
            time.sleep(2)

    # Create the vector collection only when missing.
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=384,
                distance=models.Distance.COSINE
            )
        )

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (username)
            VALUES (%s)
            ON CONFLICT (username) DO NOTHING
            """,
            (os.environ["APP_USERNAME"],)
        )

        documents = connection.execute(
            """
            SELECT id, title, content, employee_id, project_id
            FROM documents
            ORDER BY id
            """
        ).fetchall()

    # Rebuild derived storage from PostgreSQL.
    sync_all_graph()

    for document in documents:
        index_document(document)

    print("Application initialization completed.", flush=True)


if __name__ == "__main__":
    try:
        initialize_app()
    finally:
        driver.close()
        client.close()