from qdrant_client import QdrantClient

from embeddings import embed_texts


# The question we want to find information about.
question = "What technologies does Vikram know?"

# embed_texts returns a list of embeddings.
# We supplied one question, so take its first embedding.
question_vector = embed_texts([question])[0]

print("Question:", question)
print("Question embedding length:", len(question_vector))

client = QdrantClient(
    url="http://127.0.0.1:6333"
)

# Find the two most similar stored vectors.
result = client.query_points(
    collection_name="employee_documents",
    query=question_vector,
    limit=2,
    with_payload=True,
)

# Display the matching text and its source.
for rank, point in enumerate(result.points, start=1):
    payload = point.payload

    print(f"\nResult {rank}")
    print("Similarity score:", round(point.score, 4))
    print("Document ID:", payload["document_id"])
    print("Title:", payload["title"])
    print("Chunk index:", payload["chunk_index"])
    print("Text:", payload["text"])

client.close()