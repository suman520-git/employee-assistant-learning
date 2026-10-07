from qdrant_client import QdrantClient, models


# Connect to the Qdrant server running in Docker.
client = QdrantClient(
    url="http://127.0.0.1:6333"
)

collection_name = "employee_documents"

# Create the collection only if it does not already exist.
if not client.collection_exists(collection_name):

    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=384,
            distance=models.Distance.COSINE,
        ),
    )

    print("Collection created:", collection_name)

else:
    print("Collection already exists:", collection_name)

# Inspect the collection.
information = client.get_collection(collection_name)

print("Stored points:", information.points_count)

client.close()