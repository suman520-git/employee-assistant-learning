from vector_store import search_documents
from graph_store import get_graph_evidence, driver
from rag import generate_answer


question = "What skills does Meera have?"

try:
    # Retrieve document evidence.
    sources = search_documents(question, top_k=1)

    document_ids = []

    for source in sources:
        if source["document_id"] not in document_ids:
            document_ids.append(source["document_id"])

    # Retrieve graph evidence.
    graph_facts = get_graph_evidence(document_ids)

    # Generate an answer using both.
    answer = generate_answer(question, sources, graph_facts)

    print("QUESTION")
    print(question)

    print("\nANSWER")
    print(answer)

finally:
    driver.close()