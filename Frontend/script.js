async function generate() {
  const file = document.getElementById("file").files[0];
  const question = document.getElementById("question").value;

  if (!file || !question) {
    alert("Upload file + enter question");
    return;
  }

  let formData = new FormData();
  formData.append("file", file);
  formData.append("question", question);

  const output = document.getElementById("output");
  output.innerText = "⏳ Generating on GPU...";

  try {
    // ⚠️ PASTE YOUR LOCALTUNNEL URL HERE BEFORE PUSHING TO GITHUB
    const API_URL = " https://cold-women-flash.loca.lt"; 

    const res = await fetch(API_URL, {
      method: "POST",
      headers: {
        "Bypass-Tunnel-Reminder": "true" // CRITICAL for localtunnel
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