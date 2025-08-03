const input = document.getElementById("search-input");
const suggestionsList = document.getElementById("search-suggestions");
let debounceTimeout = null;
let selectedIndex = -1;
let suggestions = [];

function renderSuggestions(items) {
  suggestions = items.slice(0, 4);
  selectedIndex = -1;
  suggestionsList.innerHTML = "";

  if (suggestions.length === 0) {
    suggestionsList.style.display = "none";
    return;
  }

  for (let i = 0; i < suggestions.length; i++) {
    const li = document.createElement("li");
    li.textContent =
      suggestions[i].label || suggestions[i].name || suggestions[i];
    li.setAttribute("role", "option");
    li.setAttribute("id", `suggestion-${i}`);
    li.setAttribute("aria-selected", "false");

    li.addEventListener("mousedown", (e) => {
      e.preventDefault(); // prevent input blur
      selectSuggestion(i);
      onSuggestionChosen(suggestions[i]);
    });

    suggestionsList.appendChild(li);
  }

  suggestionsList.style.display = "block";
}

function selectSuggestion(index) {
  if (index < 0 || index >= suggestions.length) return;

  const items = suggestionsList.querySelectorAll("li");
  items.forEach((item, i) => {
    item.setAttribute("aria-selected", i === index ? "true" : "false");
  });
  suggestionsList.classList.add("selected");

  selectedIndex = index;

  const selectedItem = items[selectedIndex];
  if (selectedItem) {
    const containerTop = suggestionsList.scrollTop;
    const containerBottom = containerTop + suggestionsList.clientHeight;
    const itemTop = selectedItem.offsetTop;
    const itemBottom = itemTop + selectedItem.offsetHeight;

    if (itemTop < containerTop) {
      suggestionsList.scrollTop = itemTop;
    } else if (itemBottom > containerBottom) {
      suggestionsList.scrollTop = itemBottom - suggestionsList.clientHeight;
    }
  }

  input.value =
    suggestions[selectedIndex].label ||
    suggestions[selectedIndex].name ||
    suggestions[selectedIndex];
}

function fetchSuggestions(query) {
  clearTimeout(debounceTimeout);
  debounceTimeout = setTimeout(() => {
    if (!query.trim()) {
      // Fetch backend with empty query to get static commands/pages
      fetch("/api/search/")
        .then((res) => {
          if (!res.ok) throw new Error("Failed to fetch suggestions");
          return res.json();
        })
        .then((data) => renderSuggestions(data || []))
        .catch((err) => {
          console.error("Search fetch error:", err);
          suggestionsList.style.display = "none";
        });
      return;
    }

    fetch(`/api/search/?q=${encodeURIComponent(query.trim())}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch suggestions");
        return res.json();
      })
      .then((data) => renderSuggestions(data || []))
      .catch((err) => {
        console.error("Search fetch error:", err);
        suggestionsList.style.display = "none";
      });
  }, 100); // debounce delay
}

// On input (handles all normal changes, including empty)
input.addEventListener("input", () => {
  fetchSuggestions(input.value);
});

// On keydown for typing keys, preemptively fetch
input.addEventListener("keydown", (e) => {
  const typingKeys =
    e.key.length === 1 || e.key === "Backspace" || e.key === "Delete";

  if (typingKeys) {
    // Predict the new query before input updates
    let predictedQuery = input.value;
    if (e.key === "Backspace") {
      predictedQuery = predictedQuery.slice(0, -1);
    } else if (e.key.length === 1) {
      predictedQuery += e.key;
    }
    fetchSuggestions(predictedQuery);
  }
});

// Hide suggestions on blur after short delay
input.addEventListener("blur", () => {
  setTimeout(() => {
    suggestionsList.style.display = "none";
    selectedIndex = -1;
  }, 150);
});

function onSuggestionChosen(suggestion) {
  console.log("Chosen:", suggestion);
  suggestionsList.style.display = "none";
  selectedIndex = -1;

  if (suggestion.url) {
    window.location.href = suggestion.url;
  }
}

input.addEventListener("focus", () => {
  fetchSuggestions(input.value);
});
