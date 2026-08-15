from neo4j import GraphDatabase

uri = "bolt://127.0.0.1:7687"

username = "neo4j"
password = "Swapnil@123"

driver = GraphDatabase.driver(uri, auth=(username, password))
driver.verify_connectivity()
print("Connected!")