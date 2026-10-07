import uuid

from qdrant_client import QdrantClient, models

from chunking import split_into_chunks
from embeddings import embed_texts

import os


# client = QdrantClient(
#     url="http://127.0.0.1:6333"
# )

client = QdrantClient(
    url=os.getenv("QDRANT_URL", "http://127.0.0.1:6333")
)

COLLECTION_NAME = "employee_documents"


def index_document(document):

    # Split and embed this document.
    chunks = split_into_chunks(
        document["content"],
        chunk_size=100,
        overlap=20,
    )

    if not chunks:
        raise ValueError("Cannot index an empty document.")

    vectors = embed_texts(chunks)

    points = []

    for index in range(len(chunks)):

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

    # Select only the old chunks belonging to this document.
    document_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="document_id",
                match=models.MatchValue(
                    value=document["id"]
                ),
            )
        ]
    )

    # Remove this document's previous chunks.
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=document_filter
        ),
        wait=True,
    )

    # Store its freshly prepared chunks.
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True,
    )

    return len(points)




def search_documents(question, top_k=3):

    # Use the same model used for document embeddings.
    question_vector = embed_texts([question])[0]

    result = client.query_points(
        collection_name=COLLECTION_NAME,
        query=question_vector,
        limit=top_k,
        with_payload=True,
    )

    sources = []

    for point in result.points:
        payload = point.payload

        sources.append({
            "document_id": payload["document_id"],
            "title": payload["title"],
            "chunk_index": payload["chunk_index"],
            "text": payload["text"],
            "employee_id": payload["employee_id"],
            "project_id": payload["project_id"],
            "score": round(point.score, 4),
        })

    return sources