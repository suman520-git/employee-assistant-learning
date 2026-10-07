from database import get_connection
from graph_store import run_graph_query, driver

def sync_project_graph():


        # Read existing SQL records.
        with get_connection() as connection:
            projects = connection.execute(
                """
                SELECT id, name, description, department_id
                FROM projects
                ORDER BY id
                """
            ).fetchall()

            assignments = connection.execute(
                """
                SELECT employee_id, project_id
                FROM employee_projects
                ORDER BY project_id, employee_id
                """
            ).fetchall()

            documents = connection.execute(
                """
                SELECT id, title, employee_id, project_id
                FROM documents
                ORDER BY id
                """
            ).fetchall()


        # Keep project and document identities unique.
        run_graph_query("""
            CREATE CONSTRAINT project_id_unique IF NOT EXISTS
            FOR (p:Project) REQUIRE p.id IS UNIQUE
        """)

        run_graph_query("""
            CREATE CONSTRAINT document_id_unique IF NOT EXISTS
            FOR (d:Document) REQUIRE d.id IS UNIQUE
        """)


        # Create projects and connect them to departments.
        for project in projects:
            run_graph_query(
                """
                MATCH (d:Department {id: $department_id})
                MERGE (p:Project {id: $id})
                SET p.name = $name,
                    p.description = $description,
                    p.updated_at = datetime()
                MERGE (p)-[:BELONGS_TO]->(d)
                """,
                {
                    "id": project["id"],
                    "name": project["name"],
                    "description": project["description"],
                    "department_id": project["department_id"],
                },
            )


        # Connect employees to their assigned projects.
        for assignment in assignments:
            run_graph_query(
                """
                MATCH (e:Employee {id: $employee_id})
                MATCH (p:Project {id: $project_id})
                MERGE (e)-[:WORKS_ON]->(p)
                """,
                {
                    "employee_id": assignment["employee_id"],
                    "project_id": assignment["project_id"],
                },
            )


        # Create document nodes and their optional links.
        for document in documents:
            run_graph_query(
                """
                MERGE (d:Document {id: $id})
                SET d.name = $title,
                    d.updated_at = datetime()
                """,
                {
                    "id": document["id"],
                    "title": document["title"],
                },
            )

            if document["employee_id"] is not None:
                run_graph_query(
                    """
                    MATCH (d:Document {id: $document_id})
                    MATCH (e:Employee {id: $employee_id})
                    MERGE (d)-[:ABOUT]->(e)
                    """,
                    {
                        "document_id": document["id"],
                        "employee_id": document["employee_id"],
                    },
                )

            if document["project_id"] is not None:
                run_graph_query(
                    """
                    MATCH (d:Document {id: $document_id})
                    MATCH (p:Project {id: $project_id})
                    MERGE (d)-[:ABOUT]->(p)
                    """,
                    {
                        "document_id": document["id"],
                        "project_id": document["project_id"],
                    },
                )


        print("Projects processed:", len(projects))
        print("Assignments processed:", len(assignments))
        print("Documents processed:", len(documents))
        print("Project and document graph sync completed.")



if __name__ == "__main__":
    try:
        sync_project_graph()
    finally:
        driver.close()
        