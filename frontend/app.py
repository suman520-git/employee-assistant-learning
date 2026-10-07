import os

import requests
import streamlit as st


st.set_page_config(
    page_title="Employee Knowledge Assistant",
    layout="wide"
)

API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:8000"
).rstrip("/")

st.title("Employee Knowledge Assistant")

api_key = st.sidebar.text_input(
    "Application API key",
    type="password"
)

st.sidebar.caption("Enter the same application key used in Swagger.")


def call_api(method, path, **kwargs):
    if not api_key:
        st.warning("Enter your application API key in the sidebar.")
        return None

    try:
        response = requests.request(
            method=method,
            url=f"{API_URL}{path}",
            headers={"X-API-Key": api_key},
            timeout=(5, 180),
            **kwargs
        )
    except requests.Timeout:
        st.error(
            "The request timed out. It may still have completed. "
            "Check View records or Question history before submitting again."
        )
        return None
    except requests.ConnectionError:
        st.error("Cannot connect to FastAPI. Check that it is running.")
        return None
    except requests.RequestException:
        st.error("The API request could not be completed.")
        return None

    try:
        data = response.json()
    except ValueError:
        st.error(f"The API returned a non-JSON response ({response.status_code}).")
        return None

    if not response.ok:
        st.error(f"Request failed ({response.status_code})")
        st.write(data.get("detail", data))
        return None

    return data


def show_evidence(result):
    st.subheader("Document evidence")

    for number, source in enumerate(result["sources"], start=1):
        with st.expander(f"[D{number}] {source['title']}"):
            st.write(source["text"])
            st.caption(
                f"Document ID: {source['document_id']} | "
                f"Similarity: {source['score']}"
            )

    if not result["sources"]:
        st.info("No document evidence found.")

    st.subheader("Graph evidence")

    for number, fact in enumerate(result["graph_facts"], start=1):
        st.text(
            f"[G{number}] {fact['source']} "
            f"--{fact['relationship']}--> {fact['target']}"
        )

    if not result["graph_facts"]:
        st.info("No graph evidence found.")

page = st.sidebar.radio(
    "Page",
    ["Ask or search", "View records", "Question history", "Add data"]
)

if page == "Ask or search":
    with st.form("question_form"):
        question = st.text_input("Your question")
        action = st.radio("Action", ["Ask", "Search"])
        top_k = st.number_input(
            "Number of document chunks",
            min_value=1,
            max_value=10,
            value=3
        )
        submitted = st.form_submit_button("Submit")

    if submitted:
        if len(question.strip()) < 2:
            st.warning("Enter a question with at least two characters.")
        else:
            path = "/ask" if action == "Ask" else "/search"

            with st.spinner("Retrieving information..."):
                result = call_api(
                    "POST",
                    path,
                    json={
                        "question": question.strip(),
                        "top_k": int(top_k)
                    }
                )

            if result is not None:
                if action == "Ask":
                    st.subheader("Answer")
                    st.write(result["answer"])
                    st.caption(f"Saved question ID: {result['question_id']}")

                show_evidence(result)

elif page == "View records":
    record_type = st.selectbox(
        "Record type",
        ["employees", "departments", "projects", "documents"]
    )

    if st.button("Load records"):
        records = call_api("GET", f"/{record_type}")

        if records is not None:
            st.json(records)

elif page == "Question history":
    if st.button("Load history"):
        history = call_api("GET", "/questions", params={"limit": 10})

        if history is not None:
            if not history:
                st.info("No saved questions yet.")

            for item in history:
                with st.expander(f"#{item['id']} — {item['question']}"):
                    st.write(item["answer"])
                    st.caption(item["created_at"])
                    show_evidence(item)


elif page == "Add data":
    record_type = st.selectbox(
        "What would you like to add?",
        [
            "Department",
            "Employee",
            "Project",
            "Project assignment",
            "Document text",
            "Document upload"
        ]
    )

    st.caption(
        "Find IDs on the View records page. "
        "For optional IDs, enter 0 to leave them unselected."
    )

    # Each record type gets its own form.
    with st.form(f"add_{record_type}"):
        if record_type == "Department":
            name = st.text_input("Department name")

        elif record_type == "Employee":
            name = st.text_input("Employee name")
            department_id = st.number_input(
                "Department ID", min_value=1, step=1
            )
            manager_id = st.number_input(
                "Manager ID (optional)", min_value=0, step=1
            )
            skills_text = st.text_input(
                "Skills, separated by commas",
                placeholder="python, fastapi, neo4j"
            )

        elif record_type == "Project":
            name = st.text_input("Project name")
            description = st.text_area("Description")
            department_id = st.number_input(
                "Department ID", min_value=1, step=1
            )

        elif record_type == "Project assignment":
            employee_id = st.number_input(
                "Employee ID", min_value=1, step=1
            )
            project_id = st.number_input(
                "Project ID", min_value=1, step=1
            )

        else:
            title = st.text_input("Document title", max_chars=150)
            employee_id = st.number_input(
                "Employee ID (optional)", min_value=0, step=1
            )
            project_id = st.number_input(
                "Project ID (optional)", min_value=0, step=1
            )

            if record_type == "Document text":
                content = st.text_area(
                    "Document content", max_chars=50000
                )
            else:
                uploaded_file = st.file_uploader(
                    "Select a UTF-8 text file (maximum 200 KB)",
                    type=["txt"]
                )

        submitted = st.form_submit_button("Save")

    if submitted:
        result = None

        if record_type == "Department":
            result = call_api(
                "POST",
                "/departments",
                json={"name": name.strip()}
            )

        elif record_type == "Employee":
            skills = [
                skill.strip().lower()
                for skill in skills_text.split(",")
                if skill.strip()
            ]

            result = call_api(
                "POST",
                "/employees",
                json={
                    "name": name.strip(),
                    "department_id": int(department_id),
                    "manager_id": int(manager_id) if manager_id else None,
                    "skills": skills
                }
            )

        elif record_type == "Project":
            result = call_api(
                "POST",
                "/projects",
                json={
                    "name": name.strip(),
                    "description": description.strip(),
                    "department_id": int(department_id)
                }
            )

        elif record_type == "Project assignment":
            result = call_api(
                "POST",
                f"/projects/{int(project_id)}/employees",
                json={"employee_id": int(employee_id)}
            )

        elif record_type == "Document text":
            result = call_api(
                "POST",
                "/documents",
                json={
                    "title": title.strip(),
                    "content": content.strip(),
                    "employee_id": int(employee_id) if employee_id else None,
                    "project_id": int(project_id) if project_id else None
                }
            )

        elif record_type == "Document upload":
            if uploaded_file is None:
                st.warning("Select a text file first.")

            elif uploaded_file.size > 200000:
                st.error("The file must be no larger than 200 KB.")

            else:
                form_data = {"title": title.strip()}

                # Omit optional form fields when they are not selected.
                if employee_id:
                    form_data["employee_id"] = int(employee_id)

                if project_id:
                    form_data["project_id"] = int(project_id)

                result = call_api(
                    "POST",
                    "/documents/upload",
                    data=form_data,
                    files={
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            "text/plain"
                        )
                    }
                )

        if result is not None:
            if result.get("graph_synced") is False:
                st.warning(result["warning"])
            else:
                st.success("Saved successfully.")

            st.json(result)
