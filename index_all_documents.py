from database import get_connection
from vector_store import index_document, client, COLLECTION_NAME


# Read all source documents.
with get_connection() as connection:
    cursor = connection.execute(
        """
        SELECT id, title, content, employee_id, project_id
        FROM documents
        ORDER BY id
        """
    )

    documents = cursor.fetchall()


# Index each document using the same reusable function.
for document in documents:
    chunk_count = index_document(document)

    print(
        f"Document {document['id']}: "
        f"{document['title']} — "
        f"{chunk_count} chunk(s)"
    )


result = client.count(
    collection_name=COLLECTION_NAME,
    exact=True,
)

print("Total stored points:", result.count)

client.close()