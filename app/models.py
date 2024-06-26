current_db_integration = None
from flask import current_app
from app.integrations.database.neo4j import Neo4jDBIntegration

def set_database_integration(db_integration_instance):
  global current_db_integration
  current_db_integration = db_integration_instance


def add_entity(entity_type, data):
  global current_db_integration
  print("AYOO!!!")
  current_db_integration = Neo4jDBIntegration(database=current_app.config["SELECTED_DB"])
  print(current_db_integration._database)
  return current_db_integration.add_entity(entity_type, data)


def get_full_graph():
    return current_db_integration.get_full_graph(database=current_app.config["SELECTED_DB"])


def get_entity(entity_type, entity_id):
  return current_db_integration.get_entity(entity_type, entity_id)


def get_all_entities(entity_type):
  return current_db_integration.get_all_entities(entity_type)


def update_entity(entity_type, entity_id, data):
  return current_db_integration.update_entity(entity_type, entity_id, data)


def delete_entity(entity_type, entity_id):
  return current_db_integration.delete_entity(entity_type, entity_id)


def add_relationship(data):
  return current_db_integration.add_relationship(data)


def search_entities(search_params):
  return current_db_integration.search_entities(search_params)


def search_entities_with_type(entity_type, search_params):
  return current_db_integration.search_entities_with_type(entity_type, search_params)

def search_relationships(search_params):
  return current_db_integration.search_relationships(search_params)
