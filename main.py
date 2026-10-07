from fastapi import FastAPI
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException

from psycopg.types.json import Jsonb

from database import get_connection

from psycopg.errors import UniqueViolation

from psycopg.errors import ForeignKeyViolation

from fastapi import FastAPI, HTTPException, UploadFile, File, Form

from vector_store import index_document, search_documents

from graph_store import get_graph_evidence

from rag import generate_answer

from graph_store import (
    get_graph_evidence,
    get_employee_relationships
)

from graph_sync import sync_all_graph

from graph_store import retrieve_graph_evidence

from fastapi import Query
from question_store import save_question, get_question_history
from fastapi import Depends
from security import authenticate

import time

from fastapi import Request
from starlette.concurrency import run_in_threadpool

from request_logs import save_request_log

import os
from fastapi.middleware.cors import CORSMiddleware
# Temporary learning user.
# We will replace this with the authenticated user.

app = FastAPI(dependencies=[Depends(authenticate)])

@app.middleware("http")
async def log_api_request(request: Request, call_next):
    # Skip documentation pages and routine health checks.
    if request.url.path in {
        "/docs", "/docs/oauth2-redirect",
        "/redoc", "/openapi.json", "/health"
    }:
        return await call_next(request)

    start = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response

    finally:
        duration_ms = round(
            (time.perf_counter() - start) * 1000,
            2
        )

        try:
            await run_in_threadpool(
                save_request_log,
                getattr(request.state, "user_id", None),
                request.method,
                request.url.path,
                status_code,
                duration_ms
            )
        except Exception as error:
            # A logging failure should not replace the API response.
            print("Request logging failed:", type(error).__name__)


# Describe the information required to add an employee.




class EmployeeInput(BaseModel):
    name: str = Field(min_length=1)
    department_id: int = Field(gt=0)
    manager_id: int | None = Field(default=None, gt=0)
    skills: list[str] = Field(default_factory=list)



class DepartmentInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ProjectInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    department_id: int = Field(gt=0)

class ProjectAssignmentInput(BaseModel):
    employee_id: int = Field(gt=0)


class DocumentInput(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    content: str = Field(min_length=1, max_length=50000)
    employee_id: int | None = Field(default=None, gt=0)
    project_id: int | None = Field(default=None, gt=0)

class SearchInput(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    top_k: int = Field(default=3, ge=1, le=10)







def sync_graph_after_save(saved_record):
    try:
        sync_all_graph()
    except Exception as error:
        print("Graph synchronization failed:", type(error).__name__)

        saved_record["graph_synced"] = False
        saved_record["warning"] = (
            "Record saved in PostgreSQL, but graph synchronization failed. "
            "Run python graph_sync.py to retry. "
            "Do not submit the record again."
        )
    else:
        saved_record["graph_synced"] = True

    return saved_record


@app.get("/health")

def health():
    return {"status": "ok"}



@app.post("/employees", status_code=201)
def add_employee(employee: EmployeeInput):

    # Clean the supplied skills.
    skills = []

    for skill in employee.skills:
        cleaned_skill = skill.strip().lower()

        if cleaned_skill:
            skills.append(cleaned_skill)

    with get_connection() as connection:

        # Check that the department exists.
        cursor = connection.execute(
            "SELECT id, name FROM departments WHERE id = %s",
            (employee.department_id,),
        )

        department = cursor.fetchone()

        if department is None:
            raise HTTPException(
                status_code=422,
                detail="The selected department does not exist.",
            )

        # Check that the manager exists, if one was supplied.
        if employee.manager_id is not None:
            cursor = connection.execute(
                "SELECT id FROM employees WHERE id = %s",
                (employee.manager_id,),
            )

            manager = cursor.fetchone()

            if manager is None:
                raise HTTPException(
                    status_code=422,
                    detail="The selected manager does not exist.",
                )

# During migration, save both the department ID
# and the name required by the old column.

            cursor = connection.execute(
            """
            INSERT INTO employees (
                name,
                department_id,
                manager_id,
                skills
            )
            VALUES (%s, %s, %s, %s)
            RETURNING
                id, name, department_id, manager_id, skills
            """,
            (
                employee.name,
                employee.department_id,
                employee.manager_id,
                Jsonb(skills),
            ),
        )

        new_employee = cursor.fetchone()

    return sync_graph_after_save(new_employee)



   
@app.get("/employees")
def get_employees(skill: str | None = None):

    sql = """
        SELECT
            employee.id,
            employee.name,
            employee.department_id,
            department.name AS department,
            employee.manager_id,
            manager.name AS manager_name,
            employee.skills
        FROM employees AS employee
        LEFT JOIN departments AS department
            ON employee.department_id = department.id
        LEFT JOIN employees AS manager
            ON employee.manager_id = manager.id
    """

    parameters = ()

    if skill is not None:
        cleaned_skill = skill.strip().lower()

        if not cleaned_skill:
            raise HTTPException(
                status_code=422,
                detail="Skill must not be empty.",
            )

        sql += " WHERE employee.skills @> %s"
        parameters = (Jsonb([cleaned_skill]),)

    sql += " ORDER BY employee.id"

    with get_connection() as connection:
        cursor = connection.execute(sql, parameters)
        records = cursor.fetchall()

    return records



@app.get("/departments")
def get_departments():

    with get_connection() as connection:
        cursor = connection.execute(
            "SELECT id, name FROM departments ORDER BY id"
        )

        departments = cursor.fetchall()

    return departments



@app.post("/departments", status_code=201)
def add_department(department: DepartmentInput):

    # Remove spaces around the name.
    name = department.name.strip()

    if not name:
        raise HTTPException(
            status_code=422,
            detail="Department name must not be empty.",
        )

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO departments (name)
                VALUES (%s)
                RETURNING id, name
                """,
                (name,),
            )

            new_department = cursor.fetchone()

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="A department with this name already exists.",
        )

    return sync_graph_after_save(new_department)



@app.post("/projects", status_code=201)
def add_project(project: ProjectInput):

    name = project.name.strip()

    if not name:
        raise HTTPException(
            status_code=422,
            detail="Project name must not be empty.",
        )

    try:
        with get_connection() as connection:

            # Check that the selected department exists.
            cursor = connection.execute(
                "SELECT id FROM departments WHERE id = %s",
                (project.department_id,),
            )

            department = cursor.fetchone()

            if department is None:
                raise HTTPException(
                    status_code=422,
                    detail="The selected department does not exist.",
                )

            # Save the project.
            cursor = connection.execute(
                """
                INSERT INTO projects (
                    name, description, department_id
                )
                VALUES (%s, %s, %s)
                RETURNING id, name, description, department_id
                """,
                (
                    name,
                    project.description,
                    project.department_id,
                ),
            )

            new_project = cursor.fetchone()

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="A project with this name already exists.",
        )

    return sync_graph_after_save(new_project)


@app.get("/projects")
def get_projects():

    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT
                project.id,
                project.name,
                project.description,
                project.department_id,
                department.name AS department
            FROM projects AS project
            JOIN departments AS department
                ON project.department_id = department.id
            ORDER BY project.id
            """
        )

        projects = cursor.fetchall()

    return projects



@app.post("/projects/{project_id}/employees", status_code=201)
def assign_employee(
    project_id: int,
    assignment: ProjectAssignmentInput,
):

    try:
        with get_connection() as connection:

            # Check that the project exists.
            cursor = connection.execute(
                "SELECT id FROM projects WHERE id = %s",
                (project_id,),
            )

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Project not found.",
                )

            # Check that the employee exists.
            cursor = connection.execute(
                "SELECT id FROM employees WHERE id = %s",
                (assignment.employee_id,),
            )

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=422,
                    detail="The selected employee does not exist.",
                )

            # Save the employee–project relationship.
            cursor = connection.execute(
                """
                INSERT INTO employee_projects (
                    employee_id, project_id
                )
                VALUES (%s, %s)
                RETURNING employee_id, project_id
                """,
                (assignment.employee_id, project_id),
            )

            new_assignment = cursor.fetchone()

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="This employee is already assigned to this project.",
        )

    return sync_graph_after_save(new_assignment)



@app.get("/projects/{project_id}/employees")
def get_project_employees(project_id: int):

    with get_connection() as connection:

        # Distinguish a missing project from an empty project.
        cursor = connection.execute(
            "SELECT id FROM projects WHERE id = %s",
            (project_id,),
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Project not found.",
            )

        # Find employees assigned to this project.
        cursor = connection.execute(
            """
            SELECT
                employee.id,
                employee.name,
                employee.skills
            FROM employee_projects AS assignment
            JOIN employees AS employee
                ON assignment.employee_id = employee.id
            WHERE assignment.project_id = %s
            ORDER BY employee.id
            """,
            (project_id,),
        )

        employees = cursor.fetchall()

    return employees


def save_document(document: DocumentInput, metadata: dict):

    title = document.title.strip()
    content = document.content.strip()

    if not title or not content:
        raise HTTPException(
            status_code=422,
            detail="Document title and content must not be empty.",
        )

    try:
        with get_connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO documents (
                    title,
                    content,
                    employee_id,
                    project_id,
                    metadata
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING
                    id, title, content, employee_id,
                    project_id, metadata, created_at
                """,
                (
                    title,
                    content,
                    document.employee_id,
                    document.project_id,
                    Jsonb(metadata),
                ),
            )

            new_document = cursor.fetchone()

    except ForeignKeyViolation:
        raise HTTPException(
            status_code=422,
            detail="The selected employee or project does not exist.",
        )

        # The PostgreSQL transaction has already committed.
    # Now make the saved document searchable in Qdrant.
    try:
        chunk_count = index_document(new_document)

    except Exception as error:
        print("Document indexing failed:", error)

        raise HTTPException(
            status_code=503,
            detail={
                "message": (
                    "Document saved in PostgreSQL, but indexing failed. "
                    "Run index_all_documents.py to retry indexing. "
                    "Do not submit the document again."
                ),
                "document_id": new_document["id"],
            },
        ) from error

    new_document["indexed_chunks"] = chunk_count

    return sync_graph_after_save(new_document)

@app.post("/documents", status_code=201)
def add_document(document: DocumentInput):
    return save_document(
        document,
        metadata={"source": "api"},
    )



@app.post("/documents/upload", status_code=201)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(..., min_length=1, max_length=150),
    employee_id: int | None = Form(default=None, gt=0),
    project_id: int | None = Form(default=None, gt=0),
):

    filename = file.filename or ""

    # This learning version supports plain text files.
    if not filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=415,
            detail="Please upload a .txt file.",
        )

    # Read one byte beyond the limit so we can detect oversize files.
    data = file.file.read(200001)

    if len(data) > 200000:
        raise HTTPException(
            status_code=413,
            detail="File must be 200 KB or smaller.",
        )

    # Convert the uploaded bytes into readable text.
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422,
            detail="The file must contain UTF-8 text.",
        )

    if not content.strip():
        raise HTTPException(
            status_code=422,
            detail="The file must not be empty.",
        )

    if len(content) > 50000:
        raise HTTPException(
            status_code=413,
            detail="Document text must not exceed 50,000 characters.",
        )

    # Reuse the document input model.
    document = DocumentInput(
        title=title,
        content=content,
        employee_id=employee_id,
        project_id=project_id,
    )

    # Reuse the existing database-saving function.
    return save_document(
        document,
        metadata={
            "source": "upload",
            "filename": filename,
        },
    )












@app.get("/documents")
def get_documents():

    with get_connection() as connection:
        cursor = connection.execute(
            """
            SELECT
                document.id,
                document.title,
                document.content,
                document.employee_id,
                employee.name AS employee_name,
                document.project_id,
                project.name AS project_name,
                document.metadata,
                document.created_at
            FROM documents AS document
            LEFT JOIN employees AS employee
                ON document.employee_id = employee.id
            LEFT JOIN projects AS project
                ON document.project_id = project.id
            ORDER BY document.id
            """
        )

        documents = cursor.fetchall()

    return documents



@app.post("/search")
def search(request: SearchInput):
    question = request.question.strip()

    if len(question) < 2:
        raise HTTPException(
            status_code=422,
            detail="Question must contain at least 2 characters."
        )

    # Step 1: Retrieve relevant document chunks from Qdrant.
    try:
        sources = search_documents(
            question,
            top_k=request.top_k
        )
    except Exception as error:
        print("Vector search failed:", error)

        raise HTTPException(
            status_code=503,
            detail="Document search is unavailable. Check the server logs."
        ) from error

    # Step 2: Collect unique document IDs.
    document_ids = []

    for source in sources:
        if source["document_id"] not in document_ids:
            document_ids.append(source["document_id"])

    # Step 3: Retrieve related facts from Neo4j.
    try:
        graph_facts = retrieve_graph_evidence(
            question,
            document_ids
        )
    except Exception as error:
        print("Graph search failed:", error)

        raise HTTPException(
            status_code=503,
            detail="Graph search is unavailable. Check the server logs."
        ) from error

    # Step 4: Return both kinds of evidence.
    return {
        "question": question,
        "sources": sources,
        "graph_facts": graph_facts
    }


@app.post("/ask")
def ask(request: SearchInput,current_user: dict = Depends(authenticate)):
    question = request.question.strip()

    if len(question) < 2:
        raise HTTPException(
            status_code=422,
            detail="Question must contain at least 2 characters."
        )

    # Retrieve document chunks from Qdrant.
    try:
        sources = search_documents(
            question,
            top_k=request.top_k
        )
    except Exception as error:
        print("Vector search failed:", error)

        raise HTTPException(
            status_code=503,
            detail="Document search is unavailable."
        ) from error

    # Collect unique document IDs.
    document_ids = []

    for source in sources:
        if source["document_id"] not in document_ids:
            document_ids.append(source["document_id"])

    # Retrieve related facts from Neo4j.
    try:
        graph_facts = retrieve_graph_evidence(
            question,
            document_ids
        )
    except Exception as error:
        print("Graph search failed:", error)

        raise HTTPException(
            status_code=503,
            detail="Graph search is unavailable."
        ) from error

    # Generate an answer using both types of evidence.
    try:
        answer = generate_answer(
            question,
            sources,
            graph_facts
        )
    except Exception as error:
        print("Answer generation failed:", type(error).__name__)

        raise HTTPException(
            status_code=503,
            detail="Answer generation is unavailable. Check the server logs."
        ) from error


        # Save the answer only after generation succeeds.
    try:
        saved_question = save_question(
            user_id=current_user["id"],
            question=question,
            answer=answer,
            sources=sources,
            graph_facts=graph_facts
        )
    except Exception as error:
        print("Question history save failed:", type(error).__name__)

        raise HTTPException(
            status_code=503,
            detail="An answer was generated, but saving question history failed."
        ) from error

    return {
        "question_id": saved_question["id"],
        "created_at": saved_question["created_at"],
        "question": question,
        "answer": answer,
        "sources": sources,
        "graph_facts": graph_facts
    }
    

@app.get("/employees/{employee_id}/relationships")
def employee_relationships(employee_id: int):
    if employee_id <= 0:
        raise HTTPException(
            status_code=422,
            detail="Employee ID must be greater than zero."
        )

    # PostgreSQL is our source of truth for employee records.
    with get_connection() as connection:
        employee = connection.execute(
            "SELECT id FROM employees WHERE id = %s",
            (employee_id,)
        ).fetchone()

    if employee is None:
        raise HTTPException(
            status_code=404,
            detail="Employee not found."
        )

    try:
        result = get_employee_relationships(employee_id)
    except Exception as error:
        print("Employee graph query failed:", type(error).__name__)

        raise HTTPException(
            status_code=503,
            detail="Employee relationships are currently unavailable."
        ) from error

    # The employee exists in SQL but has not reached Neo4j.
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Employee graph data is not synced yet."
        )

    return result


@app.get("/questions")
def question_history(
    limit: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(authenticate)
):
    try:
        return get_question_history(
            user_id=current_user["id"],
            limit=limit
        )
    except Exception as error:
        print("Question history read failed:", type(error).__name__)

        raise HTTPException(
            status_code=503,
            detail="Question history is currently unavailable."
        ) from error



allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8501,http://127.0.0.1:8501"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"]
)
    