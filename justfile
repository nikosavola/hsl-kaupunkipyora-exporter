# Default to listing available recipes
default:
    @just --list

cpus := num_cpus()

# --- Installation ---

# Install the package and all development dependencies
[group('setup')]
install:
    @uv sync --all-groups
    @uv run prek install

# Clean up all build, test, coverage and Python artifacts
[confirm]
[group('setup')]
clean:
    @rm -rf dist build *.egg-info .ruff_cache .pytest_cache htmlcov coverage.xml

# --- Linting & Formatting ---

# Update pre-commit hooks to the latest revisions
[group('lint')]
update-pre:
    @uvx prek autoupdate -j $(( {{ cpus }} / 2 + {{ cpus }} % 2 ))

# Run all pre-commit hooks on all files
[group('lint')]
pre-commit:
    @uvx prek run --all-files

# --- Testing ---

# Run tests with pytest
[group('test')]
test *args:
    uv run --dev pytest -n auto {{ args }}

# --- Build ---

# Needs the project's own environment (not --no-project) since it imports
# hsl_kaupunkipyora_exporter.stations, not just the stdlib.
[doc("Regenerate the bundled station data (requires DIGITRANSIT_API_KEY).")]
[group('build')]
[script('uv', 'run', 'python')]
refresh-stations:
    import datetime
    import json
    import pathlib

    from hsl_kaupunkipyora_exporter.stations import fetch_stations

    stations = list(fetch_stations())
    assert len(stations) >= 50, f"Refusing to write only {len(stations)} station(s)."

    data = {
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "stations": sorted(
            ({"name": s.name, "lat": s.lat, "lon": s.lon} for s in stations),
            key=lambda s: s["name"],
        ),
    }

    target = pathlib.Path("src/hsl_kaupunkipyora_exporter/data/stations.json")
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(target)

    print("Bundled station data refreshed.")

# Build the Python package
[group('build')]
build:
    @rm -rf dist
    uv build

# Build the pure-Python wheel and stage it for the browser app
[group('build')]
build-web:
    @rm -rf dist web/dist
    uv build --wheel
    @mkdir -p web/dist
    @cp dist/*.whl web/dist/
    @wheel_name=$(basename dist/*.whl); \
        printf '{\n  "wheel": "%s"\n}\n' "$wheel_name" > web/dist/manifest.json
    @uv run python3 -c 'import json; from hsl_kaupunkipyora_exporter.stations import get_stations; stations = get_stations(); data = [{"name": s.name, "lat": s.lat, "lon": s.lon} for s in stations]; print(json.dumps(data, ensure_ascii=False, indent=2))' > web/dist/stations.json
    @echo "Wheel and station data staged to web/dist/."

# Serve the web app locally (builds first). Requires Python 3.
[group('build')]
serve-web port="8000": build-web
    @echo "Serving http://localhost:{{ port }}/  (Ctrl+C to stop)"
    @cd web && python3 -m http.server {{ port }}
