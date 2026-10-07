from vector_store import search_documents
from graph_store import get_graph_evidence, driver
from rag import build_context


question = "What skills does Meera have?"

try:
    # Retrieve relevant text.
    sources = search_documents(question, top_k=1)

    # Collect unique document IDs.
    document_ids = []

    for source in sources:
        if source["document_id"] not in document_ids:
            document_ids.append(source["document_id"])

    # Retrieve related relationships.
    graph_facts = get_graph_evidence(document_ids)

    # Format both types of evidence into one string.
    context = build_context(sources, graph_facts)

    print("QUESTION")
    print(question)

    print("\nCONTEXT")
    print(context)

finally:
    driver.close()