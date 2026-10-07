import os

import re

from neo4j import GraphDatabase


# driver = GraphDatabase.driver(
#     "bolt://127.0.0.1:7687",
#     auth=("neo4j", os.environ["NEO4J_PASSWORD"]),
# )

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687"),
    auth=(
        os.getenv("NEO4J_USER", "neo4j"),
        os.environ["NEO4J_PASSWORD"]
    )
)

def run_graph_query(query, parameters=None):

    with driver.session(database="neo4j") as session:
        result = session.run(query, parameters or {})

        # Read the results before closing the session.
        records = result.data()

    return records




def get_graph_evidence(document_ids):
    # No matching documents means there is nothing to expand.
    if not document_ids:
        return []

    query = """
    MATCH (document:Document)-[:ABOUT]->(entity)
    WHERE document.id IN $document_ids

    MATCH (source)-[relationship]->(target)
    WHERE source = entity OR target = entity

    RETURN DISTINCT
        source.name AS source,
        type(relationship) AS relationship,
        target.name AS target

    ORDER BY source, relationship, target
    LIMIT 50
    """

    return run_graph_query(
        query,
        {"document_ids": document_ids}
    )





def get_employee_relationships(employee_id):
    # Check whether the employee has been synced to Neo4j.
    employees = run_graph_query(
        """
        MATCH (employee:Employee {id: $employee_id})
        RETURN employee.id AS id, employee.name AS name
        """,
        {"employee_id": employee_id}
    )

    if not employees:
        return None

    # Find incoming and outgoing relationships.
    relationships = run_graph_query(
        """
        MATCH (employee:Employee {id: $employee_id})
        MATCH (source)-[relationship]->(target)
        WHERE source = employee OR target = employee

        RETURN DISTINCT
            source.name AS source,
            type(relationship) AS relationship,
            target.name AS target

        ORDER BY source, relationship, target
        """,
        {"employee_id": employee_id}
    )

    return {
        "employee": employees[0],
        "relationships": relationships
    }




def get_question_graph_evidence(question):
    # Read the names of searchable graph entities.
    entities = run_graph_query(
        """
        MATCH (entity)
        WHERE entity:Employee
           OR entity:Department
           OR entity:Project
           OR entity:Skill
        RETURN DISTINCT entity.name AS name
        """
    )

    matched_names = []

    for entity in entities:
        name = entity["name"]

        if not name:
            continue

        # Match the complete name, ignoring uppercase/lowercase.
        # For example, "Nisha" matches "What skills does Nisha have?"
        pattern = r"(?<!\w)" + re.escape(name) + r"(?!\w)"

        if re.search(pattern, question, flags=re.IGNORECASE):
            matched_names.append(name)

    if not matched_names:
        return []

    # Retrieve relationships around the matched entities.
    return run_graph_query(
        """
        MATCH (entity)
        WHERE entity.name IN $names
          AND (
              entity:Employee
              OR entity:Department
              OR entity:Project
              OR entity:Skill
          )

        MATCH (source)-[relationship]->(target)
        WHERE source = entity OR target = entity

        RETURN DISTINCT
            source.name AS source,
            type(relationship) AS relationship,
            target.name AS target

        ORDER BY source, relationship, target
        """,
        {"names": matched_names}
    )



def retrieve_graph_evidence(question, document_ids):
    # First retrieve facts around names in the question.
    question_facts = get_question_graph_evidence(question)

    # Then retrieve facts related to the document search results.
    document_facts = get_graph_evidence(document_ids)

    # Merge the lists without repeating identical facts.
    combined_facts = []

    for fact in question_facts + document_facts:
        if fact not in combined_facts:
            combined_facts.append(fact)

    return combined_facts