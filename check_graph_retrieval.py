from vector_store import search_documents
from graph_store import get_graph_evidence, driver


question = "What skills does Meera have?"

try:
    # First, retrieve the most similar document chunk.
    # Use one result so the first test is easy to follow.
    sources = search_documents(question, top_k=1)

    print("Question:", question)

    print("\nDOCUMENT EVIDENCE")

    document_ids = []

    for source in sources:
        print("Document ID:", source["document_id"])
        print("Title:", source["title"])
        print("Text:", source["text"])
        print("Score:", source["score"])

        # Multiple chunks can belong to the same document.
        if source["document_id"] not in document_ids:
            document_ids.append(source["document_id"])

    # Next, retrieve graph facts related to those documents.
    graph_facts = get_graph_evidence(document_ids)

    print("\nGRAPH EVIDENCE")

    for fact in graph_facts:
        print(
            fact["source"],
            "--",
            fact["relationship"],
            "-->",
            fact["target"]
        )

    if not graph_facts:
        print("No related graph facts found.")

finally:
    driver.close()