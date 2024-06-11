import os
from neo4j import GraphDatabase
from .base import DatabaseIntegration
from flask import current_app 

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


# rename dict keys containing spaces with _
def remove_spaces(data):
    normalized_data = {}

    for key in data:
        val = data[key]

        if " " in key:
            key = key.replace(" ", "_")

        normalized_data[key] = val

    return normalized_data


class Neo4jDBIntegration(DatabaseIntegration):
    def __init__(self, schema_file_path="schema.json", database=NEO4J_DATABASE):
        self._database = database
        self._driver = GraphDatabase.driver(
            NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD), database=database
        )
    def add_entity(self, entity_type, data):
        data["data"] = remove_spaces(data["data"])

        q = f"""CREATE (n:{entity_type})
                SET n = $attr
                RETURN elementId(n) AS id"""

        result = self._query(q, {"attr": data["data"]})

        # return entity ID
        return result[0]["id"]

    def get_full_graph(self, database=None):
        if database is None:
            database = self._database

        graph = {
            "entities": {},
            "relationships": [],
        }

        with self._driver.session(database=database) as session:
            # get nodes
            nodes = session.run(
                "MATCH (n) RETURN n, elementId(n) AS id, labels(n)[0] AS label"
            )
            for node in nodes:
                lbl = node["label"]
                id = node["id"]
                node_props = dict(node["n"])  # Convert Node object to dict

                if lbl not in graph["entities"]:
                    graph["entities"][lbl] = {}

                graph["entities"][lbl][id] = {"entity_type": lbl, "data": node_props}

            # get edges
            results = session.run(
                """
                MATCH (src)-[e]->(dest)
                RETURN elementId(src) AS src_id,
                    labels(src)[0] AS from_type,
                    type(e) AS relationship,
                    elementId(dest) AS dest_id,
                    labels(dest)[0] AS to_type,
                    properties(e) AS edge_props
                """
            )
            for row in results:
                desc = {
                    "relationship": row["relationship"],
                    "snippet": row["edge_props"].get("snippet", row["relationship"]),
                    "from_id": row["src_id"],
                    "to_id": row["dest_id"],
                    "from_type": row["from_type"],
                    "to_type": row["to_type"],
                    "from_entity": "",
                    "to_entity": "",
                    "relationship_type": row["relationship"],
                }

                graph["relationships"].append(desc)

        return graph

    def get_entity(self, entity_type, entity_id):
        q = f"""MATCH (n:{entity_type})
                WHERE elementId(n) = $id
                RETURN n"""

        result = self._query(q, {"id": entity_id})
        if len(result) == 1:
            return result[0]["n"]

        return {}

    def get_all_entities(self, entity_type):
        entities = {}

        q = f"MATCH (n:{entity_type}) RETURN n, elementId(n) AS id"

        result = self._query(q)
        for row in result:
            entities[row["id"]] = row["n"]

        return entities

    def update_entity(self, entity_type, entity_id, data):
        data["data"] = remove_spaces(data["data"])

        q = f"""MATCH (n:{entity_type})
                WHERE elementId(n) = $id
                SET n = $attr"""

        result = self._query(q, {"id": entity_id, "attr": data["data"]})

        return True

    def delete_entity(self, entity_type, entity_id):
        q = f"""MATCH (n:{entity_type})
                WHERE elementId(n) = $id
                DELETE n"""

        result = self._query(q, {"id": entity_id})

        return True

    def add_relationship(self, data):
        src_id = data["from_id"]
        dst_id = data["to_id"]
        edge_type = data["relationship"].strip().replace(" ", "_")
        src_entity = data["from_entity"]
        dst_entity = data["to_entity"]

        q = f"""MATCH (src), (dest)
                WHERE elementId(src) = $src_id AND elementId(dest) = $dest_id
                CREATE (src)-[:{edge_type}]->(dest)"""

        result = self._query(q, {"src_id": src_id, "dest_id": dst_id})

        return True

    def search_entities(self, search_params):
        search_params = remove_spaces(search_params)
        filters = " AND ".join([f"n.{key} = ${key}" for key in search_params])
        
        print('Debug: search_params after remove_spaces:', search_params)
        print('Debug: filters:', filters)
        
        q = f"""MATCH (n)
                WHERE {filters}
                RETURN n, labels(n)[0] AS label, elementId(n) AS id"""
        
        print('Debug: query:', q)
        
        nodes = self._query(q, search_params)
        
        print('Debug: raw nodes returned by query:', nodes)
        
        results = []
        for n in nodes:
            results.append({"type": n["label"], "id": n["id"], **n["n"]})
        
        print('Debug: processed results:', results)
        
        return results

    def search_entities_with_type(self, entity_type, search_params):
        search_params = remove_spaces(search_params)

        filters = " AND ".join([f"n.{key} = ${key}" for key in search_params])
        q = f"""MATCH (n:{entity_type})
                WHERE {filters}
                RETURN n, labels(n)[0] AS label, elementId(n) AS id"""

        nodes = self._query(q, search_params)

        results = []
        for n in nodes:
            results.append({"type": n["label"], "id": n["id"], **n["n"]})

        return results

    def search_relationships(self, search_params):
        search_params = remove_spaces(search_params)

        # Check if search_params contains 'name' and get the corresponding node ID
        if 'name' in search_params:
            node_name = search_params['name']
            node_query = f"""MATCH (n)
                            WHERE n.name = $name
                            RETURN elementId(n) AS id"""
            node_result = self._query(node_query, {"name": node_name})
            if node_result:
                node_id = node_result[0]["id"]
            else:
                return []
        else:
            return []

        q = f"""MATCH (src)-[e]->(dest)
                WHERE elementId(src) = $node_id OR elementId(dest) = $node_id
                RETURN elementId(src) AS from_temp_id,
                    labels(src)[0] AS from_type,
                    type(e) AS relationship,
                    elementId(dest) AS to_temp_id,
                    labels(dest)[0] AS to_type,
                    properties(e) AS edge_props"""

        print('Debug: query:', q)
        
        edges = self._query(q, {"node_id": node_id})

        results = []
        for edge in edges:
            edge_data = {
                "from_temp_id": edge["from_temp_id"],
                "to_temp_id": edge["to_temp_id"],
                "relationship": edge["relationship"],
                "from_type": edge["from_type"],
                "to_type": edge["to_type"],
                "data": edge["edge_props"]
            }
            results.append(edge_data)

        print('Debug: processed relationships:', results)

        return results



    def get_databases(self):
        q = "SHOW DATABASES"
        result = self._query(q)
        return [db["name"] for db in result]

    def _query(self, cypher, params={}):
        selected_db = current_app.config.get("SELECTED_DB", self._database)
        with self._driver.session(database=selected_db) as session:
            print("Using database:", selected_db)
            data = session.run(cypher, params)
            json_data = [r.data() for r in data]
            return json_data

