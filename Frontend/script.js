async function generate() {
    // Grab the text from the new textarea instead of the file input
    const schemaText = document.getElementById("schemaText").value;
    const question = document.getElementById("question").value;

    if (!schemaText || !question) {
      alert("Paste your schema and enter a question");
      return;
    }

    let formData = new FormData();
    // We send the string under the key "schema_text" to match FastAPI
    formData.append("schema_text", schemaText); 
    formData.append("question", question);

    const output = document.getElementById("output");
    output.innerText = "⏳ Generating on GPU...";

   try {
    // ⚠️ KEEP YOUR EXISTING LOCALTUNNEL URL HERE
    const API_URL = "https://your-backend-url.loca.lt/generate"; 

    const res = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Bypass-Tunnel-Reminder": "true" 
      },
      body: formData
    });

    const data = await res.json();
    console.log("Response:", data);

    if (data.sql) {
      output.innerText =
        "✅ SQL Query:\n\n" + data.sql +
        "\n\nConfidence: " + (data.confidence || "N/A");
    } else {
      output.innerText =
        "⚠️ " + (data.message || "Something went wrong") +
        "\n\n" + JSON.stringify(data, null, 2);
    }

  } catch (err) {
    console.error(err);
    output.innerText = "❌ Error connecting to backend. Is Colab running?";
  }
}