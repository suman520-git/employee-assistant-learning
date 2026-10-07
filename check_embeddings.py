from database import get_connection
from chunking import split_into_chunks
from embeddings import embed_texts


# Read Vikram's document.
with get_connection() as connection:
    cursor = connection.execute(
        """
        SELECT id, title, content
        FROM documents
        WHERE id = %s
        """,
        (3,),
    )

    document = cursor.fetchone()


if document is None:
    print("Document 3 was not found.")

else:
    # Keep the same demonstration settings.
    chunks = split_into_chunks(
        document["content"],
        chunk_size=15,
        overlap=3,
    )

    # Generate one embedding for each chunk.
    vectors = embed_texts(chunks)

    print("Document:", document["title"])
    print("Number of chunks:", len(chunks))
    print("Number of embeddings:", len(vectors))

    for index in range(len(chunks)):
        print(f"\nChunk {index + 1}:")
        print(chunks[index])

        print("Embedding length:", len(vectors[index]))
        print("First 5 numbers:", vectors[index][:5])