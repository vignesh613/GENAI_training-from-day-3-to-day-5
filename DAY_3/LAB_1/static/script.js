async function submitQuery() {
    const queryInput = document.getElementById("queryInput");
    const query = queryInput.value.trim();
    const resultDiv = document.getElementById("result");
    const loadingDiv = document.getElementById("loading");
    const submitBtn = document.getElementById("submitBtn");

    if (!query) {
        queryInput.focus();
        return;
    }

    // UI State: Loading
    resultDiv.classList.add("hidden");
    loadingDiv.classList.remove("hidden");
    submitBtn.disabled = true;
    submitBtn.innerText = "Processing...";

    try {
        const response = await fetch("/api/route", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query })
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }

        const data = await response.json();
        
        // Update UI
        const badge = document.getElementById("sentimentBadge");
        badge.innerText = data.sentiment;
        
        // Clear previous classes
        badge.className = "badge";
        badge.classList.add(data.sentiment.toLowerCase());

        document.getElementById("routeTaken").innerText = data.route;
        document.getElementById("responseText").innerText = data.reply;
        
        // UI State: Done
        loadingDiv.classList.add("hidden");
        resultDiv.classList.remove("hidden");
    } catch (error) {
        console.error("Routing failed", error);
        alert("An error occurred while communicating with the server.\nPlease make sure the backend is running.");
        loadingDiv.classList.add("hidden");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = "Route Message";
    }
}

// Allow pressing Ctrl+Enter to submit
document.getElementById('queryInput').addEventListener('keydown', function(e) {
  if (e.ctrlKey && e.key === 'Enter') {
    submitQuery();
  }
});
