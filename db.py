from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7688"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "gaian@12345"),
            ),
        )
    return _driver


def get_session():
    return get_driver().session()
