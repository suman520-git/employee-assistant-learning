from importlib.metadata import version
from pathlib import Path


packages = [
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("psycopg", "psycopg[binary]"),
    ("python-multipart", "python-multipart"),
    ("fastembed", "fastembed"),
    ("qdrant-client", "qdrant-client"),
    ("neo4j", "neo4j"),
    ("openai", "openai"),
    ("streamlit", "streamlit"),
    ("requests", "requests")
]

lines = []

for installed_name, requirement_name in packages:
    lines.append(
        f"{requirement_name}=={version(installed_name)}"
    )

Path("requirements.txt").write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8"
)

print("Created requirements.txt")