# This views.py file is part of a Flask web application and defines various routes for handling web requests.
# It includes imports for Flask utilities, os module for file path operations, model functions for database interactions,
# and custom signals for event triggering. A Flask Blueprint named 'main' is created to organize these routes.
# Routes include:
# - An index route that renders a template for the base URL.
# - A route for serving the favicon.
# - Routes for CRUD operations on entities, including creating, retrieving (both single and all entities), updating, and deleting.
# - A route for adding relationships between entities.
# - Routes for searching entities and relationships based on provided search parameters.
# - A special route for triggering integrations by name, allowing external functionalities to be executed.
# Each route is associated with a specific HTTP method (GET, POST, PUT, DELETE) and includes logic for handling request data,
# interacting with the database through model functions, and sending responses in JSON format. Signals are used to notify
# other parts of the application about the creation, update, or deletion of entities.

from app.integrations.database.neo4j import Neo4jDBIntegration
from .models import set_database_integration
from flask import (
    Blueprint,
    send_from_directory,
    current_app,
    jsonify,
    request,
    render_template,
)
import os, json
from neo4j import GraphDatabase, graph
from .models import (
    add_entity,
    get_full_graph,
    get_entity,
    get_all_entities,
    update_entity,
    delete_entity,
    add_relationship,
    search_entities,
    search_entities_with_type,
    search_relationships,
)
from .signals import entity_created, entity_updated, entity_deleted
from .integration_manager import get_integration_function
from .integrations.database import CurrentDBIntegration


NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")


main = Blueprint("main", __name__)


@main.route("/")
def index():
  return render_template("index.html")


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if obj is None:
            return None
        return super().default(obj)

@main.route("/get-graph-data", methods=["GET"])
def get_graph_data():
    global CurrentDBIntegration
    all_entities = CurrentDBIntegration.get_full_graph()
    db_name = CurrentDBIntegration._database
    print("Database Name:", db_name)
    print("ALL ENTITIES")
    print(all_entities)

    # Filter out None values from all_entities
    filtered_entities = {}
    for k, v in all_entities.items():
        if isinstance(v, dict):
            filtered_entities[k] = {kk: vv for kk, vv in v.items() if vv is not None}
        elif isinstance(v, list):
            filtered_entities[k] = [item for item in v if item is not None]
        else:
            filtered_entities[k] = v

    return current_app.response_class(
        json.dumps(filtered_entities, cls=CustomJSONEncoder),
        mimetype='application/json'
    )


@main.route("/favicon.ico")
def favicon():
  return send_from_directory(
      os.path.join(main.root_path, "static"),
      "favicon.ico",
      mimetype="image/vnd.microsoft.icon",
  )


@main.route("/trigger-integration/<integration_name>", methods=["POST"])
def trigger_integration(integration_name):
  print("Triggered!")
  data = request.json
  integration_function = get_integration_function(integration_name)
  if integration_function:
    # Capture the return value which should be a Flask response
    response = integration_function(current_app._get_current_object(), data)
    return response
  return jsonify(error="Integration function not found"), 404


@main.route("/<entity_type>", methods=["POST"])
def create_entity(entity_type):
  data = request.json
  entity_id = add_entity(entity_type, data)

  # Send signal for the created entity, if you want to trigger it for other types, remove the condition.
  entity_created.send(
      current_app._get_current_object(),
      entity_type=entity_type,
      entity_id=entity_id,
      data=data,
  )

  return jsonify(id=entity_id), 201


@main.route("/<entity_type>/<int:entity_id>", methods=["GET"])
def retrieve_entity(entity_type, entity_id):
  entity = get_entity(entity_type, entity_id)
  if entity:
    return jsonify(entity), 200
  return jsonify(error="Entity not found"), 404


@main.route("/<entity_type>", methods=["GET"])
def retrieve_all_entities(entity_type):
  entities = get_all_entities(entity_type)
  return jsonify(entities), 200


@main.route("/<entity_type>/<int:entity_id>", methods=["PUT"])
def update_entity_route(entity_type, entity_id):
  data = request.json
  if update_entity(entity_type, entity_id, data):
    # Send signal for the updated entity
    entity_updated.send(
        current_app._get_current_object(),
        entity_type=entity_type,
        entity_id=entity_id,
        data=data,
    )
    return jsonify(success=True), 200
  return jsonify(error="Update failed"), 404


@main.route("/<entity_type>/<entity_id>", methods=["DELETE"])
def delete_entity_route(entity_type, entity_id):
  print(f"Deleting {entity_type} with id {entity_id}")
  if delete_entity(entity_type, entity_id):
    # Send signal for the deleted entity
    entity_deleted.send(
        current_app._get_current_object(),
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return jsonify(success=True), 200
  return jsonify(error="Delete failed"), 404


@main.route("/relationship", methods=["POST"])
def create_relationship_route():
  data = request.json
  relationship_id = add_relationship(data)

  # Assuming you want to send a signal for relationship creation as well
  entity_created.send(
      current_app._get_current_object(),
      entity_type="relationship",
      entity_id=relationship_id,
      data=data,
  )

  return jsonify(id=relationship_id), 201


@main.route("/search/entities/<entity_type>", methods=["GET"])
def search_entity(entity_type):
  search_params = request.args.to_dict()

  if search_params:
    results = search_entities_with_type(entity_type, search_params)
    return jsonify(results), 200

  return jsonify(error="Missing search parameters"), 400


@main.route("/search/relationships", methods=["GET"])
def search_relationship():
  search_params = request.args.to_dict()

  if search_params:
    results = search_relationships(search_params)
    return jsonify(results), 200

  return jsonify(error="Missing search parameters"), 400


@main.route("/databases", methods=["GET"])
def get_databases():
    databases = CurrentDBIntegration.get_databases()
    return jsonify(databases), 200


@main.route("/set-database/<db_name>", methods=["POST"])
def set_database(db_name):
    global CurrentDBIntegration
    CurrentDBIntegration._driver.close()
    CurrentDBIntegration = Neo4jDBIntegration(database=db_name)
    current_app.config["SELECTED_DB"] = db_name  # Set the selected database name
    return jsonify({"message": "Database switched"}), 200


@main.route("/current-database", methods=["GET"])
def current_database():
    global CurrentDBIntegration
    return jsonify({"current_db_integration": CurrentDBIntegration.__class__.__name__}), 200


# Add more routes as needed for specific actions, queries, etc.

