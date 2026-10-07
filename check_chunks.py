from database import get_connection
from chunking import split_into_chunks


# Read Vikram's saved document.
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
    # Small settings make the splitting visible for this short document.
    chunks = split_into_chunks(
        document["content"],
        chunk_size=15,
        overlap=3,
    )

    print("Document ID:", document["id"])
    print("Title:", document["title"])
    print("Number of chunks:", len(chunks))

    for number, chunk in enumerate(chunks, start=1):
        print(f"\nChunk {number}:")
        print(chunk)