from psycopg.types.json import Jsonb

from database import get_connection


def save_question(user_id, question, answer, sources, graph_facts):
    with get_connection() as connection:
        saved_question = connection.execute(
            """
            INSERT INTO questions (
                user_id, question, answer, sources, graph_facts
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (
                user_id,
                question,
                answer,
                Jsonb(sources),
                Jsonb(graph_facts)
            )
        ).fetchone()

    return saved_question


def get_question_history(user_id, limit):
    with get_connection() as connection:
        history = connection.execute(
            """
            SELECT
                id, question, answer,
                sources, graph_facts, created_at
            FROM questions
            WHERE user_id = %s
            ORDER BY id DESC
            LIMIT %s
            """,
            (user_id, limit)
        ).fetchall()

    return history