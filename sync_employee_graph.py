from database import get_connection
from graph_store import run_graph_query, driver



def sync_employee_graph():

                # Read the existing PostgreSQL records.
                with get_connection() as connection:
                    departments = connection.execute(
                        "SELECT id, name FROM departments ORDER BY id"
                    ).fetchall()

                    employees = connection.execute(
                        """
                        SELECT id, name, department_id, manager_id, skills
                        FROM employees
                        ORDER BY id
                        """
                    ).fetchall()


                # Prevent duplicate entity identities.
                run_graph_query("""
                    CREATE CONSTRAINT department_id_unique IF NOT EXISTS
                    FOR (d:Department) REQUIRE d.id IS UNIQUE
                """)

                run_graph_query("""
                    CREATE CONSTRAINT employee_id_unique IF NOT EXISTS
                    FOR (e:Employee) REQUIRE e.id IS UNIQUE
                """)

                run_graph_query("""
                    CREATE CONSTRAINT skill_name_unique IF NOT EXISTS
                    FOR (s:Skill) REQUIRE s.name IS UNIQUE
                """)


                # Create department nodes.
                for department in departments:
                    run_graph_query(
                        """
                        MERGE (d:Department {id: $id})
                        SET d.name = $name,
                            d.updated_at = datetime()
                        """,
                        {
                            "id": department["id"],
                            "name": department["name"],
                        },
                    )


                # Create ALL employee nodes before connecting managers.
                for employee in employees:
                    run_graph_query(
                        """
                        MERGE (e:Employee {id: $id})
                        SET e.name = $name,
                            e.updated_at = datetime()
                        """,
                        {
                            "id": employee["id"],
                            "name": employee["name"],
                        },
                    )


                # Create relationships for each employee.
                for employee in employees:

                    run_graph_query(
                        """
                        MATCH (e:Employee {id: $employee_id})
                        MATCH (d:Department {id: $department_id})
                        MERGE (e)-[:WORKS_IN]->(d)
                        """,
                        {
                            "employee_id": employee["id"],
                            "department_id": employee["department_id"],
                        },
                    )

                    if employee["manager_id"] is not None:
                        run_graph_query(
                            """
                            MATCH (e:Employee {id: $employee_id})
                            MATCH (m:Employee {id: $manager_id})
                            MERGE (e)-[:REPORTS_TO]->(m)
                            """,
                            {
                                "employee_id": employee["id"],
                                "manager_id": employee["manager_id"],
                            },
                        )

                    for skill in employee["skills"]:
                        run_graph_query(
                            """
                            MATCH (e:Employee {id: $employee_id})
                            MERGE (s:Skill {name: $skill})
                            MERGE (e)-[:HAS_SKILL]->(s)
                            """,
                            {
                                "employee_id": employee["id"],
                                "skill": skill,
                            },
                        )


                print("Departments processed:", len(departments))
                print("Employees processed:", len(employees))
                print("Employee graph sync completed.")



if __name__ == "__main__":
    try:
        sync_employee_graph()
    finally:
        driver.close()