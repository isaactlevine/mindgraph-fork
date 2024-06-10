import os
import openai
from app.integrations.database.neo4j import Neo4jDBIntegration
import json

def get_database_summary(database_name):
    db_integration = Neo4jDBIntegration(database=database_name)
    result = db_integration._query("MATCH (n) RETURN n")
    nodes = [record["n"] for record in result]
    
    result = db_integration._query("MATCH ()-[r]->() RETURN r")
    relationships = [record["r"] for record in result]
    
    return {
        "nodes": nodes,
        "relationships": relationships
    }

def summarize_and_store_graph(app, database_name):
    # Retrieve the details of the knowledge graph
    graph_data = get_database_summary(database_name)

    # Pass the graph data to GPT-4 for summarization
    openai.api_key = os.environ["OPENAI_API_KEY"]
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes knowledge graph data."},
                {"role": "user", "content": f"Please summarize the following knowledge graph data:\n\n{graph_data}"}
            ],
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.7,
        )
        
        # Extract the summary from the GPT-4 response
        summary = response.choices[0].message['content'].strip()
        print("88888888888888888888888")
        print(summary)
        
        # Store the summary in the globally available dictionary
        if "GRAPH_SUMMARIES" not in app.config:
            app.config["GRAPH_SUMMARIES"] = {}
        
        app.config["GRAPH_SUMMARIES"][database_name] = summary
        
        # Save the summaries to a JSON file
        with open('graph_summaries.json', 'w') as f:
            json.dump(app.config["GRAPH_SUMMARIES"], f)
        
    except Exception as e:
        print(f"Error summarizing graph data: {e}")
        # Handle the error appropriately, e.g., return an error response or raise an exception

def print_graph_summaries(app):
    try:
        with open('graph_summaries.json', 'r') as f:
            app.config["GRAPH_SUMMARIES"] = json.load(f)
    except FileNotFoundError:
        print("No graph summaries found.")
        return
    
    for db_name, summary in app.config["GRAPH_SUMMARIES"].items():
        print(f"Database: {db_name}\nSummary: {summary}\n")

def load_graph_summaries(app):
    try:
        with open('graph_summaries.json', 'r') as f:
            app.config["GRAPH_SUMMARIES"] = json.load(f)
    except FileNotFoundError:
        app.config["GRAPH_SUMMARIES"] = {}

# if __name__ == "__main__":
#     from flask import Flask
#     app = Flask(__name__)
    
#     # Load existing graph summaries
#     load_graph_summaries(app)
    
#     # # Assuming you have already summarized and stored some graphs
#     summarize_and_store_graph(app, "bibibibi")
    
#     # Now print the graph summaries
#     print_graph_summaries(app)