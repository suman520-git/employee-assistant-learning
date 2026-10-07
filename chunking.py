def split_into_chunks(text, chunk_size=100, overlap=20):

    # Check that the settings allow us to move forward.
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "Use chunk_size > 0 and 0 <= overlap < chunk_size."
        )

    # Split text into words, including across line breaks.
    words = text.split()

    chunks = []
    start = 0

    while start < len(words):

        # Select the words for this chunk.
        end = start + chunk_size
        chunk_words = words[start:end]

        # Join them into a readable string.
        chunk_text = " ".join(chunk_words)
        chunks.append(chunk_text)

        # Stop once this chunk includes the document's final word.
        if end >= len(words):
            break

        # Move forward, retaining some words as overlap.
        start = end - overlap

    return chunks