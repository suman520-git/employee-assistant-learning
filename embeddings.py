from fastembed import TextEmbedding

import os


# Load the embedding model.
# The first run downloads its files.
# embedding_model = TextEmbedding(
#     model_name="sentence-transformers/all-MiniLM-L6-v2"
# )

embedding_model = TextEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    cache_dir=os.getenv("EMBEDDING_CACHE_DIR")
)


def embed_texts(texts):
    vectors = []

    # Generate one embedding for each supplied text.
    for embedding in embedding_model.embed(texts):

        # Convert the numerical array into a regular Python list.
        vector = embedding.tolist()

        vectors.append(vector)

    return vectors