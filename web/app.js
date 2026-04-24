"use strict";

// ---------------------------------------------------------------------------
// i18n Dictionary
// ---------------------------------------------------------------------------
const i18n = {
  en: {
    "header-desc":
      "Export your Helsinki City Bike ride history as Strava-compatible GPX or TCX files — right in your browser.",
    "step1-title": '<span class="step">1</span> Provide ride history',
    "step1-hint":
      'Open your <a href="https://www.hsl.fi/en/my-information/citybikes/ride-history" target="_blank" rel="noopener noreferrer">HSL ride history page</a>, then save the whole page as HTML (<kbd>Ctrl+S</kbd>) or copy-paste the ride section below.',
    "drop-zone-text":
      "Drop an HTML or text file here, or <strong>click to browse</strong>",
    "or-divider": "— or paste the text below —",
    "paste-placeholder": "Paste your ride history text here …",
    "step2-title": '<span class="step">2</span> Options',
    "format-label": "Export format",
    "format-tcx": "TCX (recommended)",
    "format-gpx": "GPX",
    "path-label": "Path mode",
    "path-summary": "Summary only",
    "path-linear": "Linear path",
    "path-routed": "Routed path (API key required)",
    "api-key-label": "Digitransit API key",
    optional: "(optional)",
    "api-key-placeholder":
      "For station coordinates and recommended cycling route — get a free key at digitransit.fi",
    "api-key-hint":
      "Required for coordinates. Without it, rides that can't be matched to bundled station data will be skipped.",
    "get-key-link": "Get a key.",
    "step3-title": '<span class="step">3</span> Export',
    "btn-loading": "Loading Pyodide…",
    "btn-export": "Export rides",
    "btn-error": "Pyodide failed",
    "btn-proc": '<span class="spinner"></span> Processing…',
    "log-title": "Log",
    "footer-powered": "Powered by",
    "status-no-input":
      "Please provide ride history data (upload a file or paste text).",
    "status-no-api-key": "An API key is required for Routed path mode.",
    "status-no-files": "No files generated.",
    "status-ready": "{count} file(s) ready",
    "status-error": "Error — see log",
    "btn-download-all": "⬇ Download all files",
    "btn-download": "Download",
    "log-loading-rt": "Loading Pyodide runtime …",
    "log-resolving": "Resolving application wheel …",
    "log-installing": "Installing Python packages …",
    "log-loading-app": "Loading application entry point …",
    "log-ready": "Ready ✓",
    "log-fetch-station": "Fetching station coordinates from Digitransit …",
    "log-loaded-stations": "Loaded {count} stations.",
    "log-fallback-fetch":
      "Could not fetch live stations: {msg} — trying fallback dataset …",
    "log-fallback-loaded": "Loaded {count} stations from fallback dataset.",
    "log-fallback-err":
      "Could not load fallback stations: {msg} — rides will be skipped if coordinates are unknown.",
    "log-no-rides":
      "No ride files were generated. Check that your input contains valid ride data and that station data is available.",
    "log-generated": "Generated {count} file(s).",
    "log-proc-error": "Processing error: {err}",
    "log-pyodide-err": "Failed to initialize Pyodide: {err}",
  },
  fi: {
    "header-desc":
      "Muuta HSL:n kaupunkipyörien ajohistoriasi Strava-yhteensopiviksi TCX- tai GPX-tiedostoiksi suoraan selaimessa.",
    "step1-title": '<span class="step">1</span> Anna ajohistoria',
    "step1-hint":
      'Avaa <a href="https://www.hsl.fi/omat-tiedot/kaupunkipyorat/matkahistoria" target="_blank" rel="noopener noreferrer">HSL:n ajohistoriasivu</a>, tallenna sitten koko sivu HTML-tiedostona (<kbd>Ctrl+S</kbd>) tai kopioi ajohistorian osuus alle.',
    "drop-zone-text":
      "Pudota HTML- tai tekstitiedosto tähän, tai <strong>selaa klikkaamalla</strong>",
    "or-divider": "— tai liitä teksti alle —",
    "paste-placeholder": "Liitä ajohistoriasi tähän…",
    "step2-title": '<span class="step">2</span> Asetukset',
    "format-label": "Tiedostomuoto",
    "format-tcx": "TCX (suositeltu)",
    "format-gpx": "GPX",
    "path-label": "Reititystapa",
    "path-summary": "Vain yhteenveto",
    "path-linear": "Suora reitti",
    "path-routed": "Reititetty polku (vaatii API-avaimen)",
    "api-key-label": "Digitransit API-avain",
    optional: "(valinnainen)",
    "api-key-placeholder":
      "Asemien koordinaatteja ja reititettyä polkua varten — hae digitransit.fi-sivustolta",
    "api-key-hint":
      "Vaaditaan reititettyyn polkuun. Ilman tätä asemadata voi myös olla vanhentunut.",
    "get-key-link": "Hanki avain.",
    "step3-title": '<span class="step">3</span> Vie',
    "btn-loading": "Ladataan Pyodideä…",
    "btn-export": "Vie ajot",
    "btn-error": "Pyodiden lataus epäonnistui",
    "btn-proc": '<span class="spinner"></span> Käsitellään…',
    "log-title": "Loki",
    "footer-powered": "Toimii kirjastolla",
    "status-no-input":
      "Anna ajohistoriadata (lataa tiedosto tai liitä teksti).",
    "status-no-api-key": "Reititetty polku vaatii API-avaimen.",
    "status-no-files": "Ei luotuja tiedostoja.",
    "status-ready": "{count} tiedosto(a) valmiina",
    "status-error": "Virhe — katso loki",
    "btn-download-all": "⬇ Lataa kaikki tiedostot",
    "btn-download": "Lataa",
    "log-loading-rt": "Ladataan Pyodide-ajoympäristöä …",
    "log-resolving": "Selvitetään sovelluspakettia …",
    "log-installing": "Asennetaan Python-paketteja …",
    "log-loading-app": "Ladataan sovelluksen aloituspistettä …",
    "log-ready": "Valmis ✓",
    "log-fetch-station": "Haetaan asemien koordinaatteja Digitransitista …",
    "log-loaded-stations": "Ladattu {count} asemaa.",
    "log-fallback-fetch":
      "Ei voitu hakea live-asemia: {msg} — yritetään varadataa …",
    "log-fallback-loaded": "Ladattu {count} asemaa varadatasta.",
    "log-fallback-err":
      "Varadataa ei voitu ladata: {msg} — ajot ohitetaan, jos koordinaatteja ei tunneta.",
    "log-no-rides":
      "Ajotiedostoja ei luotu. Tarkista, että syöte sisältää kelvollista ajodataa ja että asemadata on saatavilla.",
    "log-generated": "Luotu {count} tiedosto(a).",
    "log-proc-error": "Käsittelyvirhe: {err}",
    "log-pyodide-err": "Pyodiden alustus epäonnistui: {err}",
  },
  sv: {
    "header-desc":
      "Exportera din HRT-stadscykel-historik som Strava-kompatibla TCX- eller GPX-filer direkt i din webbläsare.",
    "step1-title": '<span class="step">1</span> Ange resehistorik',
    "step1-hint":
      'Öppna din <a href="https://www.hsl.fi/sv/mina-uppgifter/stadscyklar/rental-history" target="_blank" rel="noopener noreferrer">HRT resehistoriksida</a>, spara sedan hela sidan som HTML (<kbd>Ctrl+S</kbd>) eller kopiera och klistra in resedelen nedan.',
    "drop-zone-text":
      "Släpp en HTML- eller textfil här, eller <strong>klicka för att bläddra</strong>",
    "or-divider": "— eller klistra in texten nedan —",
    "paste-placeholder": "Klistra in din resehistoriktext…",
    "step2-title": '<span class="step">2</span> Alternativ',
    "format-label": "Exportformat",
    "format-tcx": "TCX (rekommenderas)",
    "format-gpx": "GPX",
    "path-label": "Routingsmetoder",
    "path-summary": "Endast sammanfattning",
    "path-linear": "Rak linje",
    "path-routed": "Rekommenderad cykelrutt (kräver API-nyckel)",
    "api-key-label": "Digitransit API-nyckel",
    optional: "(frivillig)",
    "api-key-placeholder":
      "För stationskoordinater och rekommenderad cykelrutt — hämta en gratis nyckel på digitransit.fi",
    "api-key-hint":
      "Krävs för koordinater. Utan den hoppas stationer som inte kan matchas över.",
    "get-key-link": "Hämta en nyckel.",
    "step3-title": '<span class="step">3</span> Exportera',
    "btn-loading": "Laddar Pyodide…",
    "btn-export": "Exportera resor",
    "btn-error": "Pyodide misslyckades",
    "btn-proc": '<span class="spinner"></span> Bearbetar…',
    "log-title": "Logg",
    "footer-powered": "Fungerar med",
    "status-no-input":
      "Vänligen ange resehistorik (ladda upp en fil eller klistra in text).",
    "status-no-api-key": "En API-nyckel krävs för Riktig cykelrutt.",
    "status-no-files": "Inga filer genererade.",
    "status-ready": "{count} fil(er) klara",
    "status-error": "Fel — se loggen",
    "btn-download-all": "⬇ Ladda ner alla filer",
    "btn-download": "Ladda ner",
    "log-loading-rt": "Laddar Pyodide-miljö …",
    "log-resolving": "Hittar applikationspaket …",
    "log-installing": "Installerar Python-paket …",
    "log-loading-app": "Laddar applikationens startpunkt …",
    "log-ready": "Klar ✓",
    "log-fetch-station": "Hämtar stationskoordinater från Digitransit …",
    "log-loaded-stations": "Laddade {count} stationer.",
    "log-fallback-fetch":
      "Kunde inte hämta live-stationer: {msg} — försöker med reservdata …",
    "log-fallback-loaded": "Laddade {count} stationer från reservdata.",
    "log-fallback-err":
      "Kunde inte ladda reservstationer: {msg} — turer hoppas över om koordinater är okända.",
    "log-no-rides":
      "Inga resefiler skapades. Kontrollera att inmatningen innehåller giltig resedata och att stationsdata finns tillgänglig.",
    "log-generated": "Skapade {count} fil(er).",
    "log-proc-error": "Bearbetningsfel: {err}",
    "log-pyodide-err": "Kunde inte initiera Pyodide: {err}",
  },
};

const browserLang = (
  navigator.language ||
  navigator.userLanguage ||
  "en"
).toLowerCase();
let currentLang = "en";
if (browserLang.startsWith("fi")) currentLang = "fi";
else if (browserLang.startsWith("sv")) currentLang = "sv";

function t(key, params = {}) {
  let text = i18n[currentLang][key] || i18n["en"][key] || key;
  for (const [k, v] of Object.entries(params)) {
    text = text.replace(`{${k}}`, v);
  }
  return text;
}

function updateTranslations() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.innerHTML = t(el.getAttribute("data-i18n"));
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder")));
  });
  document.documentElement.lang = currentLang;

  // Update dynamic elements
  if (pyReady && !exportBtn.disabled) {
    exportBtnText.innerHTML = t("btn-export");
  } else if (!pyReady && exportBtnText.innerHTML.includes("Pyodide")) {
    exportBtnText.innerHTML = t(
      pyReady === false && exportBtn.disabled && statusText.textContent
        ? "btn-error"
        : "btn-loading",
    );
  } else if (exportBtn.disabled) {
    exportBtnText.innerHTML = t("btn-proc");
  }

  // Update result buttons if any
  document.querySelectorAll(".btn-download-all").forEach((el) => {
    el.textContent = t("btn-download-all");
  });
  document.querySelectorAll(".result-item a").forEach((el) => {
    el.textContent = t("btn-download");
  });
}

const langBtns = document.querySelectorAll(".lang-btn");
langBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    const lang = btn.getAttribute("data-lang");
    if (!lang || lang === currentLang) return;

    // Update active class
    langBtns.forEach((b) => {
      b.classList.remove("active");
      b.setAttribute("aria-pressed", "false");
    });
    btn.classList.add("active");
    btn.setAttribute("aria-pressed", "true");

    currentLang = lang;
    updateTranslations();
  });
});

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
    log(t("log-loading-rt"));
    // loadPyodide is exposed globally by the pyodide.js script tag.
    pyodide = await loadPyodide({ indexURL: PYODIDE_INDEX_URL });

    log(t("log-resolving"));
    const manifest = await loadManifest();
    const wheelUrl = new URL(`./dist/${manifest.wheel}`, window.location.href)
      .href;

    log(t("log-installing"));
    await pyodide.loadPackage("micropip");
    const micropip = pyodide.pyimport("micropip");
    // beautifulsoup4, gpxpy, polyline are resolved by micropip from PyPI.
    // The app wheel is served locally.
    await micropip.install(["polyline", "pyodide-http", wheelUrl]);

    log(t("log-loading-app"));
    const mainPy = await fetchText(MAIN_PY_URL, "main.py");
    pyodide.runPython(mainPy);
    log(t("log-ready"));

    pyReady = true;
    exportBtn.disabled = false;
    exportBtnText.textContent = t("btn-export");
  } catch (err) {
    log(t("log-pyodide-err", { err: err }), "error");
    exportBtnText.textContent = t("btn-error");
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
    log(t("status-no-input"), "warn");
    return;
  }

  const fmt = formatSelect.value;
  const pathMode = pathSelect.value;
  const includePoints = pathMode !== "summary";
  const useRoute = pathMode === "routed";
  const apiKey = apiKeyInput.value.trim();

  if (useRoute && !apiKey) {
    log(t("status-no-api-key"), "error");
    return;
  }

  exportBtn.disabled = true;
  exportBtnText.innerHTML = t("btn-proc");
  statusText.textContent = "";

  try {
    let stationsJson = "[]";
    try {
      log(t("log-fetch-station"));
      const stations = await fetchStations(apiKey || undefined);
      stationsJson = JSON.stringify(stations);
      log(t("log-loaded-stations", { count: stations.length }));
    } catch (err) {
      log(t("log-fallback-fetch", { msg: err.message }), "warn");
      try {
        const stations = await loadFallbackStations();
        stationsJson = JSON.stringify(stations);
        log(t("log-fallback-loaded", { count: stations.length }));
      } catch (fallbackErr) {
        log(t("log-fallback-err", { msg: fallbackErr.message }), "warn");
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
      log(t("log-no-rides"), "warn");
      statusText.textContent = t("status-no-files");
      return;
    }

    log(t("log-generated", { count: resultList.length }));
    statusText.textContent = t("status-ready", { count: resultList.length });
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
      link.textContent = t("btn-download");
      div.appendChild(nameSpan);
      div.appendChild(link);
      resultsDiv.appendChild(div);
    }

    if (files.length > 1) {
      const btn = document.createElement("button");
      btn.className = "btn btn-download-all";
      btn.textContent = t("btn-download-all");
      btn.addEventListener("click", () => downloadAllFiles(files));
      resultsDiv.appendChild(btn);
    }
  } catch (err) {
    log(t("log-proc-error", { err: err }), "error");
    statusText.textContent = t("status-error");
  } finally {
    exportBtn.disabled = false;
    exportBtnText.textContent = t("btn-export");
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
// Initialize language based on default or browser settings
const activeBtn = document.querySelector(
  `.lang-btn[data-lang="${currentLang}"]`,
);
if (activeBtn) {
  document.querySelectorAll(".lang-btn").forEach((b) => {
    b.classList.remove("active");
    b.setAttribute("aria-pressed", "false");
  });
  activeBtn.classList.add("active");
  activeBtn.setAttribute("aria-pressed", "true");
}

updateTranslations();
initPyodide();
