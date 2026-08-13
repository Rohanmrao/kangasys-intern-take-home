let devices = [];

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {"Content-Type": "application/json"},
    ...options
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }

  if (response.status === 204) return null;
  return response.json();
}

function formatTime(value) {
  return new Date(value).toLocaleString();
}

async function loadDevices() {
  devices = await api("/api/devices");

  document.getElementById("deviceCount").textContent = `${devices.length} device(s)`;

  const deviceHtml = devices.map(d => `
    <article class="device">
      <h3>${escapeHtml(d.name)}</h3>
      <div class="meta">${escapeHtml(d.id)} · ${escapeHtml(d.type)}</div>
      <span class="badge ${d.status}">${d.status}</span>
      <p>Unit: ${escapeHtml(d.unit)}</p>
      <p>Normal range: ${
        d.normal_min === null ? "not configured" :
        `${d.normal_min} – ${d.normal_max} ${escapeHtml(d.unit)}`
      }</p>
    </article>
  `).join("");

  document.getElementById("devices").innerHTML =
    deviceHtml || `<p class="empty">No devices yet.</p>`;

  const selects = [document.getElementById("deviceSelect"), document.getElementById("formDevice")];
  selects.forEach(select => {
    const old = select.value;
    select.innerHTML = devices.map(d =>
      `<option value="${escapeHtml(d.id)}">${escapeHtml(d.name)}</option>`
    ).join("");
    if ([...select.options].some(o => o.value === old)) select.value = old;
  });

  if (devices.length) {
    await loadReadings();
  } else {
    document.getElementById("readings").innerHTML = `<p class="empty">No readings.</p>`;
  }
}

async function loadReadings() {
  const deviceId = document.getElementById("deviceSelect").value;
  if (!deviceId) return;

  const readings = await api(`/api/devices/${encodeURIComponent(deviceId)}/readings`);

  if (!readings.length) {
    document.getElementById("readings").innerHTML = `<p class="empty">No readings for this device.</p>`;
    return;
  }

  document.getElementById("readings").innerHTML = `
    <table>
      <thead><tr><th>Time</th><th>Value</th><th>Unit</th></tr></thead>
      <tbody>
        ${readings.slice(0, 20).map(r => `
          <tr>
            <td>${formatTime(r.timestamp)}</td>
            <td>${r.value}</td>
            <td>${escapeHtml(r.unit)}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

async function loadAlerts() {
  const alerts = await api("/api/alerts?resolved=false");
  document.getElementById("alertCount").textContent = `${alerts.length} unresolved`;

  document.getElementById("alerts").innerHTML = alerts.length
    ? alerts.map(a => `
      <div class="alert">
        <div>
          <strong>${escapeHtml(a.message)}</strong>
          <div class="meta">${formatTime(a.timestamp)} · reading #${a.reading_id}</div>
        </div>
        <button onclick="resolveAlert(${a.id})">Resolve</button>
      </div>
    `).join("")
    : `<p class="empty">No active alerts.</p>`;
}

async function resolveAlert(id) {
  try {
    await api(`/api/alerts/${id}/resolve`, {method: "PATCH"});
    await loadAlerts();
  } catch (error) {
    alert(error.message);
  }
}

document.getElementById("deviceSelect").addEventListener("change", loadReadings);
document.getElementById("refreshBtn").addEventListener("click", refreshAll);

document.getElementById("readingForm").addEventListener("submit", async event => {
  event.preventDefault();

  const deviceId = document.getElementById("formDevice").value;
  const timestampInput = document.getElementById("formTimestamp").value;

  const payload = {
    value: Number(document.getElementById("formValue").value),
    unit: document.getElementById("formUnit").value.trim()
  };

  if (timestampInput) {
    payload.timestamp = new Date(timestampInput).toISOString();
  }

  try {
    await api(`/api/devices/${encodeURIComponent(deviceId)}/readings`, {
      method: "POST",
      body: JSON.stringify(payload)
    });

    document.getElementById("formMessage").textContent =
      "Reading submitted successfully. Refreshing alerts...";
    document.getElementById("readingForm").reset();

    const selected = devices.find(d => d.id === deviceId);
    if (selected) document.getElementById("formUnit").value = selected.unit;

    await refreshAll();
  } catch (error) {
    document.getElementById("formMessage").textContent = error.message;
  }
});

document.getElementById("formDevice").addEventListener("change", event => {
  const selected = devices.find(d => d.id === event.target.value);
  if (selected) document.getElementById("formUnit").value = selected.unit;
});

async function refreshAll() {
  try {
    await loadDevices();
    await loadAlerts();
  } catch (error) {
    alert(error.message);
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

refreshAll();
