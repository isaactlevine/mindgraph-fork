$(document).ready(function () {
  // Fetch available databases and populate the dropdown
  fetch("/databases")
    .then((response) => response.json())
    .then((databases) => {
      const dbSelector = $("#db-selector");
      databases.forEach((db) => {
        dbSelector.append(new Option(db, db));
      });
    });

  // Event listener for database selection
  $("#db-selector").change(function () {
    const selectedDb = $(this).val();
    fetch(`/set-database/${selectedDb}`, { method: "POST" })
      .then((response) => response.json())
      .then((data) => {
        console.log("Database switched:", data);
        fetchAndUpdateGraph(); // Refresh the graph with the new database
      })
      .catch((error) => console.error("Error switching database:", error));
  });

  var cy = cytoscape({
    container: document.getElementById("cy"),
    elements: [
      // Elements will be dynamically added later
    ],
    style: [
      // Generic node style
      {
        selector: "node",
        style: {
          content: "data(name)",
          "text-valign": "center",
          color: "black",
          "background-color": "#DDD", // Default color
          shape: "rectangle",
          width: "label",
          height: "label",
          padding: "10px",
          "font-size": "12px",
          "text-wrap": "wrap",
          "text-max-width": "80px",
        },
      },
      // Generic edge style
      {
        selector: "edge",
        style: {
          label: "data(relationship)",
          width: 2,
          "line-color": "#ccc",
          "target-arrow-color": "#ccc",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          "text-margin-y": "-10px",
          "font-size": "10px",
        },
      },
      // Node type specific styles
      {
        selector: 'node[type="Person"]',
        style: { "background-color": "#FF8A80" },
      },
      {
        selector: 'node[type="Organization"]',
        style: { "background-color": "#80D8FF" },
      },
      {
        selector: 'node[type="Object"]',
        style: { "background-color": "#FFFF8D" },
      },
      {
        selector: 'node[type="Concept"]',
        style: { "background-color": "#CCFF90" },
      },
      {
        selector: 'node[type="Event"]',
        style: { "background-color": "#CF94DA" },
      },
      {
        selector: 'node[type="Action"]',
        style: { "background-color": "#FFD180" },
      },
      {
        selector: 'node[type="Location"]',
        style: { "background-color": "#A7FFEB" },
      },
      {
        selector: 'node[type="Time"]',
        style: { "background-color": "#FF9E80" },
      },
      {
        selector: 'node[type="Technology"]',
        style: { "background-color": "#B388FF" },
      },
      {
        selector: 'node[type="Market"]',
        style: { "background-color": "#8C9EFF" },
      },
      {
        selector: 'node[type="Product"]',
        style: { "background-color": "#FFC400" },
      },
      // Highlighted style
      {
        selector: ".highlighted",
        style: {
          "background-color": "#61bffc",
          "line-color": "#61bffc",
          "target-arrow-color": "#61bffc",
          "transition-property":
            "background-color, line-color, target-arrow-color",
          "transition-duration": "0.5s",
        },
      },
    ],
    layout: {
      name: "cose",
    },
  });

  $("#search-btn").on("click", function () {
    var query = $("#search-box").val();
    
    // Show placeholder in the sidebar
    $("#sidebar").html("<p>Finding the most relevant graph...</p>");
    
    // Delay the AJAX request slightly to ensure the placeholder is rendered
    setTimeout(function() {
      // Perform the AJAX request to the dynamic endpoint
      fetch("/trigger-integration/ai_search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(query),
      })
        .then((response) => response.json())
        .then((data) => {
          console.log("Success:", data);
          answer = data.answer;
          triplets = data.triplets;
          console.log("Success:", answer);
          $("#answer").html("<small>" + triplets + "</small></br>" + answer) // Show the selected database
          $("#db-selector").val(data.selected_db); // Set the selected database in the dropdown

          // Set the database on the server
          fetch(`/set-database/${data.selected_db}`, { method: "POST" })
            .then((response) => response.json())
            .then((dbData) => {
              console.log("Database switched:", dbData);
              fetchAndUpdateGraph(); // Refresh the graph with the new database
            })
            .catch((error) => console.error("Error switching database:", error));

          var results = cy.elements().filter(function (element) {
            var name = element.data("name");
            return name && name.toLowerCase().includes(query.toLowerCase());
          });

          cy.elements().removeClass("highlighted");
          results.addClass("highlighted");
          // Update the sidebar with search results
          console.log('11111111')
          console.log(results)
          $("#sidebar").html("");
          showSelectedDatabase(data.selected_db);
        })
        .catch((error) => console.error("Error:", error));
    }, 100); // 100ms delay to ensure the placeholder is rendered
  });

  // Function to update sidebar with search results
  function updateSidebarWithSearchResults(elements) {
    var sidebarContent = "";
    elements.forEach(function (ele) {
      sidebarContent += "<p>" + ele.data("name") + "</p>";
    });
    $("#sidebar").html(sidebarContent);
  }

  function deleteNode(nodeId) {
    // Retrieve the node from cytoscape using its ID
    var node = cy.$id(nodeId);

    // Extract entityType and entityId from the node data
    var entityType = node.data("type");
    var entityId = node.data("id"); // Assuming this is the entity ID you need

    // Make an AJAX call to your Flask delete endpoint
    fetch("/" + entityType + "/" + entityId, {
      method: "DELETE",
    })
      .then((response) => {
        if (response.ok) {
          console.log("Delete successful");
          // Remove the node from cytoscape
          node.remove();
          // Update UI accordingly
          $("#sidebar").html("<p>Node deleted.</p>");
        } else {
          console.error("Delete failed");
          // Handle deletion error (optional)
          $("#sidebar").html("<p>Delete failed.</p>");
        }
      })
      .catch((error) => console.error("Error:", error));
  }

  // Listen for cytoscape node click events and update the sidebar
  cy.on("tap", "node", function (evt) {
    var node = evt.target;
    var deleteButtonHtml = "<button id='deleteBtn'>Delete</button>";
    $("#sidebar").html(
      "<h2>" +
        node.data("name") +
        "</h2><p>Details about " +
        node.data("name") +
        "</p>" +
        deleteButtonHtml
    );

    // Attach the click event handler to the delete button
    $("#deleteBtn").on("click", function () {
      deleteNode(node.id());
    });
  });

  function transformDataToCytoscapeFormat(data) {
    const { entities, relationships } = data;

    const nodes = [];
    Object.entries(entities).forEach(([entityType, entityGroup]) => {
        Object.entries(entityGroup).forEach(([entityId, entityData]) => {
            const name = entityData.data.name || entityData.data.term || "Unnamed"; // Check for both 'name' and 'term'
            nodes.push({
                data: {
                    id: entityId,
                    name: name, // Ensure name is defined
                    type: entityType,
                },
            });
        });
    });

    const edges = relationships.map((rel) => ({
        data: {
            id: "rel-" + rel.from_id + "-" + rel.to_id,
            source: rel.from_id.toString(),
            target: rel.to_id.toString(),
            relationship: rel.snippet,
            label: rel.relationship_type,
        },
    }));

    return { nodes, edges };
}

  function updateGraphVisualization(data) {
    console.log("Updating graph visualization");
    console.log("Received data:", data); // Debug: Log received data

    // Clear the current graph
    cy.elements().remove();

    // Transform and add the new nodes and edges to the graph
    const cytoscapeData = transformDataToCytoscapeFormat(data);
    console.log("Cytoscape data (nodes and edges):", cytoscapeData); // Debug: Log transformed data

    cy.add([...cytoscapeData.nodes, ...cytoscapeData.edges]);

    // Relayout the graph
    cy.layout({
      name: "cose",
    }).run();

    // Fit the graph to the viewport
    cy.fit();
  }

  function fetchAndUpdateGraph() {
    fetch("/get-graph-data")
      .then((response) => response.json())
      .then((data) => {
        // Assuming you have a function to update the graph with new data
        console.log('sending data')
        console.log(data);
        updateGraphVisualization(data);
      })
      .catch((error) => {
        console.error("Error fetching graph data:", error);
      });
  }
  // Call fetchAndUpdateGraph every 5 seconds
  // setInterval(fetchAndUpdateGraph, 10000);

  // Call fetchAndUpdateGraph to initially populate or refresh the graph
  $("#refresh-btn").click(function () {
    fetchAndUpdateGraph();
  });

  $("#add-data-btn").click(function () {
    $("#add-data-form").show(); // Show the Add Data form
  });

  $("#submit-data-btn").click(function () {
    $("#add-data-form").hide();
    const inputType = $("#input-type-selector").val(); // Get the selected input type
    console.log("inputType");
    console.log(inputType);
    const data = $("#data-box").val(); // Get the data from the textbox

    // Determine the endpoint and body based on the selected input type
    let endpoint = "";
    let body = {};

    if (inputType === "url_input") {
      const escapedData = encodeURIComponent(data);
      endpoint = "/trigger-integration/url_input";
      body = { natural_input: escapedData };
    } else if (inputType === "natural_input") {
      // For Natural Input
      endpoint = `/trigger-integration/natural_input`;
      body = { natural_input: data };
      console.log(body);
    } else {
      // For Latent Input, use raw data
      endpoint = `/trigger-integration/${inputType}`; // Dynamically set endpoint
      body = { natural_input: data }; // Use non-escaped data
    }

    // Convert the body object to a JSON string
    const jsonBody = JSON.stringify(body);
    console.log(jsonBody);

    // Perform the AJAX request to the dynamic endpoint
    fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: jsonBody,
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Success:", data);
        $("#add-data-form").hide();
        $("#data-box").val(""); // Clear the textbox
        fetchAndUpdateGraph();
      })
      .catch((error) => console.error("Error:", error));
  });

  $("#csv-upload-btn").on("click", function () {
    var fileInput = $("#csv-file-input")[0];

    if (fileInput.files.length > 0) {
      var file = fileInput.files[0];
      var reader = new FileReader();

      reader.onload = function (e) {
        var csvData = e.target.result;
        console.log(csvData);
        // Parse the CSV data to extract URLs from the first column
        var urls = csvData
          .split("\n")
          .map(function (line) {
            var columns = line.split(",");
            return columns[0].trim(); // Assuming URLs are in the first column
          })
          .filter(function (url) {
            // Optional: Filter out empty lines or non-URL data if necessary
            return url.startsWith("http://") || url.startsWith("https://");
          });
        console.log(JSON.stringify({ urls: urls }));
        // Send the array of URLs to the backend
        fetch("/trigger-integration/url_array_processor", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ urls: urls }), // Send the URLs array
        })
          .then((response) => response.json())
          .then((data) => {
            console.log("URL processing success:", data);
            // Optionally refresh the graph or update the UI here based on 'data'
          })
          .catch((error) => {
            console.error("Error processing URLs:", error);
          });
      };

      reader.readAsText(file);
    } else {
      alert("Please select a CSV file to upload.");
    }
  });

  $("#csv-file-input").change(function () {
    // Handle file selection feedback
    var fileName = $(this).val().split("\\").pop();
    console.log("File selected:", fileName);
    // Optionally, update the UI to show the selected file name
  });

  // Show selected database in sidebar for 3 seconds
  function showSelectedDatabase(selectedDb) {
    const dbInfo = $('<div>').text(`Selected Database: ${selectedDb}`);
    $('#sidebar').append(dbInfo);
    setTimeout(() => dbInfo.remove(), 10000);
  }

  // Handle AI search
  $('#ai-search-btn').click(function() {
    const query = $('#ai-search-input').val();
    console.log("Query:", query);
    
    fetch(`/ai-search?q=${encodeURIComponent(query)}`)
      .then(response => response.json())
      .then(data => {
        console.log("Received data:", data);
        console.log("Selected Database:", data.selected_db);
        showSelectedDatabase(data.selected_db);
        
        console.log("Search Quality Reflection:", data.search_quality_reflection);
        console.log("Search Quality Score:", data.search_quality_score);
        console.log("Result:", data.result);
        
        $('#search-quality-reflection').text(data.search_quality_reflection);
        $('#search-quality-score').text(data.search_quality_score);
        $('#result').html(data.result);
      })
      .catch(error => console.error('Error:', error));
  });
});


