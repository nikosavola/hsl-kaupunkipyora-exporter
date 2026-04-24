"use strict";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const PYODIDE_VERSION = "0.27.5";
const PYODIDE_INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const DIGITRANSIT_URL = "https://api.digitransit.fi/routing/v2/hsl/gtfs/v1";
const STATION_QUERY = JSON.stringify({
  query: "{ vehicleRentalStations { name lat lon } }",
});
const MANIFEST_URL = "./dist/manifest.json";
const STATIONS_FALLBACK_URL = "./dist/stations.json";
const MAIN_PY_URL = "./main.py";

// ---------------------------------------------------------------------------
// Logging helpers
// ---------------------------------------------------------------------------
const logEl = document.getElementById("log");
const logCard = document.getElementById("logCard");

function log(msg, level = "info") {
  logCard.classList.remove("hidden");
  const prefix =
    level === "error" ? "ERROR: " : level === "warn" ? "WARN: " : "";
  logEl.textContent += prefix + msg + "\n";
  logEl.scrollTop = logEl.scrollHeight;
}

// Global bridge so Python can call back into JS for logging.
globalThis._pyLog = log;

// ---------------------------------------------------------------------------
// UI references
// ---------------------------------------------------------------------------
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const fileNameEl = document.getElementById("fileName");
const textInput = document.getElementById("textInput");
const formatSelect = document.getElementById("formatSelect");
const pathSelect = document.getElementById("pathSelect");
const apiKeyInput = document.getElementById("apiKey");
const exportBtn = document.getElementById("exportBtn");
const exportBtnText = document.getElementById("exportBtnText");
const statusText = document.getElementById("statusText");
const resultsDiv = document.getElementById("results");

let uploadedContent = null;

// ---------------------------------------------------------------------------
// File handling
// ---------------------------------------------------------------------------
fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (!file) return;
  fileNameEl.textContent = file.name;
  fileNameEl.classList.remove("hidden");
  const reader = new FileReader();
  reader.onload = () => {
    uploadedContent = reader.result;
  };
  reader.readAsText(file);
});

for (const evt of ["dragover", "dragenter"]) {
  dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
  });
}
for (const evt of ["dragleave", "drop"]) {
  dropZone.addEventListener(evt, () => dropZone.classList.remove("drag-over"));
}
dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  const file = e.dataTransfer.files[0];
  if (file) {
    fileInput.files = e.dataTransfer.files;
    fileInput.dispatchEvent(new Event("change"));
  }
});

// ---------------------------------------------------------------------------
// Pyodide bootstrap
// ---------------------------------------------------------------------------
let pyodide = null;
let pyReady = false;

async function fetchText(url, label) {
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`Failed to load ${label} (${url}): HTTP ${resp.status}`);
  }
  return resp.text();
}

async function loadManifest() {
  const resp = await fetch(MANIFEST_URL);
  if (!resp.ok) {
    throw new Error(
      `Could not load ${MANIFEST_URL} (HTTP ${resp.status}). ` +
        `Did you run the web build step? Try 'just build-web'.`,
    );
  }
  return resp.json();
}

async function loadFallbackStations() {
  const resp = await fetch(STATIONS_FALLBACK_URL);
  if (!resp.ok) {
    throw new Error(
      `Fallback station data not available (HTTP ${resp.status})`,
    );
  }
  return resp.json();
}

async function initPyodide() {
  try {
    log("Loading Pyodide runtime …");
    // loadPyodide is exposed globally by the pyodide.js script tag.
    pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX_URL });

    log("Resolving application wheel …");
    const manifest = await loadManifest();
    const wheelUrl = new URL(`./dist/${manifest.wheel}`, window.location.href)
      .href;

    log("Installing Python packages …");
    await pyodide.loadPackage("micropip");
    const micropip = pyodide.pyimport("micropip");
    // beautifulsoup4, gpxpy, polyline are resolved by micropip from PyPI.
    // The app wheel is served locally.
    await micropip.install(["polyline", "pyodide-http", wheelUrl]);

    log("Loading application entry point …");
    const mainPy = await fetchText(MAIN_PY_URL, "main.py");
    pyodide.runPython(mainPy);
    log("Ready ✓");

    pyReady = true;
    exportBtn.disabled = false;
    exportBtnText.textContent = "Export rides";
  } catch (err) {
    log("Failed to initialize Pyodide: " + err, "error");
    exportBtnText.textContent = "Pyodide failed";
  }
}

// ---------------------------------------------------------------------------
// Station fetching (JS side — keeps network off the Pyodide worker)
// ---------------------------------------------------------------------------
async function fetchStations(apiKey) {
  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["digitransit-subscription-key"] = apiKey;

  const resp = await fetch(DIGITRANSIT_URL, {
    method: "POST",
    headers,
    body: STATION_QUERY,
  });
  if (!resp.ok) throw new Error(`Station API returned HTTP ${resp.status}`);
  const data = await resp.json();
  const raw = data && data.data && data.data.vehicleRentalStations;
  if (!Array.isArray(raw)) throw new Error("Unexpected station API response");
  return raw;
}

// ---------------------------------------------------------------------------
// Export logic
// ---------------------------------------------------------------------------
exportBtn.addEventListener("click", runExport);

async function runExport() {
  if (!pyReady) return;
  resultsDiv.classList.add("hidden");
  resultsDiv.innerHTML = "";

  const content = uploadedContent || textInput.value.trim();
  if (!content) {
    log(
      "Please provide ride history data (upload a file or paste text).",
      "warn",
    );
    return;
  }

  const fmt = formatSelect.value;
  const pathMode = pathSelect.value;
  const includePoints = pathMode !== "summary";
  const useRoute = pathMode === "routed";
  const apiKey = apiKeyInput.value.trim();

  if (useRoute && !apiKey) {
    log("An API key is required for Routed path mode.", "error");
    return;
  }

  exportBtn.disabled = true;
  exportBtnText.innerHTML = '<span class="spinner"></span> Processing…';
  statusText.textContent = "";

  try {
    let stationsJson = "[]";
    try {
      log("Fetching station coordinates from Digitransit …");
      const stations = await fetchStations(apiKey || undefined);
      stationsJson = JSON.stringify(stations);
      log(`Loaded ${stations.length} stations.`);
    } catch (err) {
      log(
        `Could not fetch live stations: ${err.message} — trying fallback dataset …`,
        "warn",
      );
      try {
        const stations = await loadFallbackStations();
        stationsJson = JSON.stringify(stations);
        log(`Loaded ${stations.length} stations from fallback dataset.`);
      } catch (fallbackErr) {
        log(
          `Could not load fallback stations: ${fallbackErr.message} — rides will be skipped if coordinates are unknown.`,
          "warn",
        );
      }
    }

    const processRides = pyodide.globals.get("process_rides");
    let resultProxy;
    try {
      resultProxy = processRides(
        content,
        stationsJson,
        fmt,
        includePoints,
        useRoute,
        apiKey || undefined,
      );
    } finally {
      processRides.destroy();
    }
    const resultList = resultProxy.toJs();
    resultProxy.destroy();

    if (!resultList || resultList.length === 0) {
      log(
        "No ride files were generated. Check that your input contains valid ride data and that station data is available.",
        "warn",
      );
      statusText.textContent = "No files generated.";
      return;
    }

    log(`Generated ${resultList.length} file(s).`);
    statusText.textContent = `${resultList.length} file(s) ready`;
    resultsDiv.classList.remove("hidden");

    const files = [];
    for (const item of resultList) {
      const [fname, fileContent] = item;
      const blob = new Blob([fileContent], { type: "application/xml" });
      const url = URL.createObjectURL(blob);
      files.push({ fname, url });

      const div = document.createElement("div");
      div.className = "result-item";
      const nameSpan = document.createElement("span");
      nameSpan.className = "name";
      nameSpan.textContent = fname;
      const link = document.createElement("a");
      link.href = url;
      link.download = fname;
      link.textContent = "Download";
      div.appendChild(nameSpan);
      div.appendChild(link);
      resultsDiv.appendChild(div);
    }

    if (files.length > 1) {
      const btn = document.createElement("button");
      btn.className = "btn btn-download-all";
      btn.textContent = "⬇ Download all files";
      btn.addEventListener("click", () => downloadAllFiles(files));
      resultsDiv.appendChild(btn);
    }
  } catch (err) {
    log("Processing error: " + err, "error");
    statusText.textContent = "Error — see log";
  } finally {
    exportBtn.disabled = false;
    exportBtnText.textContent = "Export rides";
  }
}

function downloadAllFiles(files) {
  for (const { url, fname } of files) {
    const a = document.createElement("a");
    a.href = url;
    a.download = fname;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
initPyodide();
