import os

from neo4j import GraphDatabase


uri = "bolt://127.0.0.1:7687"
username = "neo4j"
password = os.environ["NEO4J_PASSWORD"]

# Create the driver and check the connection.
with GraphDatabase.driver(
    uri,
    auth=(username, password),
) as driver:

    driver.verify_connectivity()

    print("Connected to Neo4j successfully.")