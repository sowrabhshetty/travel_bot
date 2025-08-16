document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('detailedTripForm');
  const resultsDiv = document.getElementById('results');
  const placeTypesContainer = document.getElementById('placeTypesCheckboxes');

  if (!form || !resultsDiv || !placeTypesContainer) return;

  // TODO: Replace with your Render URL when ready, e.g. "https://your-app.onrender.com"
  const BACKEND_BASE_URL = ""; // leave empty until you paste the Render URL
  const USE_MOCK = false; // set true to test UI without backend

  // Loading indicator
  const loadingIndicator = document.createElement('div');
  loadingIndicator.id = 'loadingIndicator';
  loadingIndicator.className = 'text-center py-3';
  loadingIndicator.innerHTML = '<div class="spinner-border text-primary" role="status"></div><div class="mt-2">Finding great matches…</div>';

  function getSelectedPlaceTypes() {
    const checked = placeTypesContainer.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checked).map((c) => c.value);
  }

  function buildResultCard(city) {
    const types = (city.matching_types || []).map(t => `<span class="badge text-bg-primary me-1 mb-1">${t}</span>`).join(' ');
    const score = typeof city.match_score === 'number' ? city.match_score : city.match_score || 0;

    return `
      <div class="card mb-3">
        ${city.image ? `<img src="${city.image}" class="card-img-top" alt="${city.name}">` : ""}
        <div class="card-body">
          <h5 class="card-title mb-1">${city.name || 'Unknown Destination'}</h5>
          <p class="text-muted mb-2">${city.country || ''}</p>
          <p class="mb-2">Match Score: <strong>${score}%</strong></p>
          ${types ? `<div class="mb-2">${types}</div>` : ""}
          ${city.description ? `<p class="card-text mb-0">${city.description}</p>` : ""}
        </div>
      </div>
    `;
  }

  function showEmptyState() {
    resultsDiv.innerHTML = `
      <div class="alert alert-warning" role="alert">
        No cities match the criteria. Please adjust preferences and try again.
      </div>
    `;
  }

  async function fetchRecommendations(payload) {
    if (USE_MOCK || !BACKEND_BASE_URL) {
      // Mocked data for UI testing
      await new Promise(res => setTimeout(res, 800));
      return {
        cities: [
          {
            name: "Lisbon",
            country: "Portugal",
            match_score: 87,
            matching_types: ["city", "beach"],
            description: "Sunny European capital with great food and views.",
            image: "https://images.unsplash.com/photo-1520975916090-3105956dac38"
          },
          {
            name: "Chiang Mai",
            country: "Thailand",
            match_score: 81,
            matching_types: ["mountain", "city"],
            description: "Cultural hub with mountains, temples, and night markets.",
            image: "https://images.unsplash.com/photo-1544989164-31dc3c645987"
          }
        ]
      };
    }

    const res = await fetch(`${BACKEND_BASE_URL.replace(/\/$/, '')}/api/recommendations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`Server error ${res.status}: ${text}`);
    }
    return res.json();
  }

  form.addEventListener('submit', async function (e) {
    e.preventDefault();

    // Read inputs
    const budget = Number(document.getElementById('budget')?.value || 0);
    const duration = Number(document.getElementById('duration')?.value || 0);
    const weather = document.getElementById('weather')?.value || '';
    const continent = document.getElementById('continent')?.value || '';
    const types = getSelectedPlaceTypes();

    const payload = {
      budget,
      duration,
      weather,
      continent,
      types
    };

    // Clear and show loading
    resultsDiv.innerHTML = '';
    resultsDiv.appendChild(loadingIndicator);

    try {
      const data = await fetchRecommendations(payload);
      const cities = Array.isArray(data?.cities) ? data.cities : [];

      if (!cities.length) {
        resultsDiv.removeChild(loadingIndicator);
        showEmptyState();
        return;
      }

      let html = `<h4>Top Matches</h4>`;
      html += cities.map(buildResultCard).join('');
      resultsDiv.innerHTML = html;
    } catch (err) {
      resultsDiv.innerHTML = `
        <div class="alert alert-danger" role="alert">
          Something went wrong while fetching recommendations. ${err.message ? `<br><small>${err.message}</small>` : ""}
        </div>
      `;
    } finally {
      if (resultsDiv.contains(loadingIndicator)) {
        resultsDiv.removeChild(loadingIndicator);
      }
    }
  });
});
