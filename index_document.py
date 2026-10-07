import uuid

from qdrant_client import QdrantClient, models

from database import get_connection
from chunking import split_into_chunks
from embeddings import embed_texts


# Read Vikram's document from PostgreSQL.
with get_connection() as connection:
    cursor = connection.execute(
        """
        SELECT id, title, content, employee_id, project_id
        FROM documents
        WHERE id = %s
        """,
        (3,),
    )

    document = cursor.fetchone()


if document is None:
    raise ValueError("Document 3 was not found.")


# Use the same settings as our chunking demonstration.
chunks = split_into_chunks(
    document["content"],
    chunk_size=15,
    overlap=3,
)

# Generate one embedding per chunk.
vectors = embed_texts(chunks)

# Prepare the records that Qdrant will store.
points = []

for index in range(len(chunks)):

    # The same document ID and chunk index produce the same UUID.
    point_id = str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"document:{document['id']}:chunk:{index}",
        )
    )

    point = models.PointStruct(
        id=point_id,
        vector=vectors[index],
        payload={
            "document_id": document["id"],
            "title": document["title"],
            "chunk_index": index,
            "text": chunks[index],
            "employee_id": document["employee_id"],
            "project_id": document["project_id"],
        },
    )

    points.append(point)


# Connect to the existing Qdrant collection.
client = QdrantClient(
    url="http://127.0.0.1:6333"
)

collection_name = "employee_documents"

# Insert new points, or replace points with the same IDs.
client.upsert(
    collection_name=collection_name,
    points=points,
    wait=True,
)

print("Document indexed:", document["title"])
print("Chunks saved:", len(points))

# Ask Qdrant how many points are stored.
result = client.count(
    collection_name=collection_name,
    exact=True,
)

print("Total stored points:", result.count)

client.close()