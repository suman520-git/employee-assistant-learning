from sync_employee_graph import sync_employee_graph
from sync_project_graph import sync_project_graph


def sync_all_graph():
    # Create departments and employees first.
    sync_employee_graph()

    # Projects, assignments, and documents reference those nodes.
    sync_project_graph()


if __name__ == "__main__":
    from graph_store import driver

    try:
        sync_all_graph()
    finally:
        driver.close()