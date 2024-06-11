import os
import openai
from flask import jsonify, current_app
import json
from app.models import get_full_graph, search_entities, search_relationships
from kg_selection import load_graph_summaries
from sklearn.metrics.pairwise import cosine_similarity
from openai.embeddings_utils import get_embedding

openai.api_key = os.getenv('OPENAI_API_KEY')


def collect_connections(nodes, edges):
    graph = get_full_graph()
    triplets = []

    # Create a lookup for node names
    node_id_to_name = {node['id']: node['name'] for node in nodes}
    
    # Add nodes from the graph to the lookup
    for entity_type, entity_dict in graph['entities'].items():
        for node_id, node_data in entity_dict.items():
            if node_id not in node_id_to_name:
                node_id_to_name[node_id] = node_data['data'].get('name', 'Unknown')

    # Directly process the edges to construct triplets
    for edge in edges:
        from_id = edge['from_temp_id']
        to_id = edge['to_temp_id']
        relationship_type = edge['relationship']
        from_node_name = node_id_to_name.get(from_id, 'Unknown')
        to_node_name = node_id_to_name.get(to_id, 'Unknown')
        triplet = f"{from_node_name} {relationship_type} {to_node_name}"
        triplets.append(triplet)

    # Find all additional triplets for each node in the input list
    for node in nodes:
        if 'temp_id' in node:
            node_temp_id = node['temp_id']
            additional_triplets = find_connected_triplets(node_temp_id, graph, node_id_to_name)
            triplets.extend(additional_triplets)

    return triplets

def find_connected_triplets(node_id, graph, node_id_to_name, exclude_id=None):
    connected_triplets = []
    for relationship in graph['relationships']:
        if (relationship['from_id'] == node_id and relationship['to_id'] != exclude_id) or (relationship['to_id'] == node_id and relationship['from_id'] != exclude_id):
            from_node_name = node_id_to_name.get(relationship['from_id'], 'Unknown')
            to_node_name = node_id_to_name.get(relationship['to_id'], 'Unknown')
            relationship_type = relationship.get('relationship', 'connected to')
            triplet = f"{from_node_name} {relationship_type} {to_node_name}"
            print(triplet)
            connected_triplets.append(triplet)

    return connected_triplets


def generate_search_parameters(input_text):
  try:
      response = openai.ChatCompletion.create(
          model="gpt-3.5-turbo",
          messages=[
              {"role": "system", "content": """You are a helpful assistant expected to generate search parameters in an array format for entities and relationships based on the given user input. Output should be in array format that looks like this with "name" as the key for every parameter. User: Did Johnny Appleseed plant apple seeds? Assistant:{"name":"John","name":"Appleseed","name":"Apple","name":"Seed"}."""},
              {"role": "user", "content": f"User input:{input_text}"}
          ],
          #response_format={"type": "json_object"}
      )
      search_parameters = response.choices[0].message['content']
      print("search_para: ", search_parameters)
      return json.loads(search_parameters)
  except Exception as e:
      print(f"Error generating search parameters: {e}")
      return []


def ai_search(app, input_text):
    print("ai_search start")
    with app.app_context():
        # Load the graph summaries
        # Load the graph summaries
        load_graph_summaries(app)

        # Print the loaded graph summaries
        print("wazzzzap")
        print("Loaded Graph Summaries:")
        print(app.config["GRAPH_SUMMARIES"])

        # Get the embedding of the user's search query
        query_embedding = get_embedding(input_text, engine="text-embedding-ada-002")

        # Calculate the cosine similarity between the search query and each graph summary
        max_similarity = -1
        selected_db = None
        for db_name, summary in app.config["GRAPH_SUMMARIES"].items():
            summary_embedding = get_embedding(summary, engine="text-embedding-ada-002")
            similarity = cosine_similarity([query_embedding], [summary_embedding])[0][0]
            if similarity > max_similarity:
                max_similarity = similarity
                selected_db = db_name

        print("Selected Database:", selected_db)
        
        if selected_db is None:
            return jsonify({"error": "No suitable database found for the search query"}), 400
        current_app.config["SELECTED_DB"] = selected_db
        # Generate search parameters based on the user's input
        search_parameters = generate_search_parameters(input_text)
        print("search_parameters", search_parameters)
        if not search_parameters:
            return jsonify({"error": "Failed to generate search parameters"}), 400

        graph = get_full_graph()
        entity_results = []
        relationship_results = []

        # Iterate through each dictionary in the list of dictionaries
        for param in search_parameters:
            print('yup')
            print(param)
            # Assuming each dictionary in the list has only one key-value pair you want to use
            for key, value in param.items():
                param_dict = {key: value}
                print(f"param_dict: {param_dict}")
                entity_results.extend(search_entities(param_dict))
                relationship_results.extend(search_relationships(param_dict))
    

        print("entity_results: ", entity_results)
        print("relationship_results: ", relationship_results)
        # Now expecting a single list of triplets instead of two separate lists
        triplets = collect_connections(entity_results, relationship_results)
        print("triplet: ", triplets)

        # Construct a message to send to GPT based on triplets
        if triplets:
            message = f"Based on the user input '{input_text}', here are the relationships found: {', '.join(triplets)}. Simply state the relations in natural language concisely."
        else:
            message = f"Based on the user input '{input_text}', no specific relationships were found. Generate a general insight."

        print("message: ", message)

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You're an assistant that generates a concise answer to the uer input based on the data provided following the user input."},
                    {"role": "user", "content": message}
                ]
            )
            # Assuming the model's response is directly usable
            answer = response.choices[0].message['content']
            print("answer: ", answer)
            return jsonify({"answer": answer, "triplets":str(triplets), "selected_db": selected_db}), 200
        except Exception as e:
            print(f"Error processing AI search: {e}")
            return jsonify({"error": str(e)}), 500

def register(integration_manager):
    integration_manager.register('ai_search', ai_search)


