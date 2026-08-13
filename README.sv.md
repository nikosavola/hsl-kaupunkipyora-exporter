# HSL Kaupunkipyörä Exporter

[![en](https://img.shields.io/badge/lang-en-red.svg)](./README.md)
[![fi](https://img.shields.io/badge/lang-fi-blue.svg)](./README.fi.md)
[![sv](https://img.shields.io/badge/lang-sv-yellow.svg)](./README.sv.md)

[![Quality gate status](https://sonarcloud.io/api/project_badges/measure?project=nikosavola_hsl-kaupunkipyora-exporter&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=nikosavola_hsl-kaupunkipyora-exporter)
[![Tests](https://github.com/nikosavola/hsl-kaupunkipyora-exporter/actions/workflows/test.yml/badge.svg)](https://github.com/nikosavola/hsl-kaupunkipyora-exporter/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/nikosavola/hsl-kaupunkipyora-exporter/branch/main/graph/badge.svg)](https://codecov.io/gh/nikosavola/hsl-kaupunkipyora-exporter)
[![PyPI](https://img.shields.io/pypi/v/hsl-kaupunkipyora-exporter.svg)](https://pypi.org/project/hsl-kaupunkipyora-exporter/)
[![License](https://img.shields.io/github/license/nikosavola/hsl-kaupunkipyora-exporter.svg)](LICENSE)

Exportera din [HRT-stadscykel](https://www.hsl.fi/sv/mina-uppgifter/stadscyklar/rental-history)-historik som
Strava-kompatibla TCX- eller GPX-filer.

> För fullständig dokumentation, se den [engelska](./README.md) eller den [finska](./README.fi.md) versionen.

## Installation

Kräver Python 3.13+. Det är enklast att köra verktyget med [`uvx`](https://docs.astral.sh/uv/)::

```bash
uvx hsl-kaupunkipyora-exporter rides.txt
```

## AI-agent

Det här repot har en [skill](skills/hsl-bike-export/SKILL.md) för Claude Code som kör verktyget via naturligt språk.
Installera med:

```bash
npx skills add nikosavola/hsl-kaupunkipyora-exporter
```

## Användning

1. Öppna din resehistorik på <https://www.hsl.fi/sv/mina-uppgifter/stadscyklar/rental-history>.
1. Spara sajten som HTML (`Ctrl+S`) eller kopiera resehistoriktexten till en `.txt`-fil.
1. Kör verktyget:

```bash
uvx hsl-kaupunkipyora-exporter rides.html
```

## Routingsmetoder

- **Sammanfattning**: Endast sträcka och tid från HRT, inga GPS-punkter.
- `--linear`: Rak linje mellan stationerna.
- `--use-route`: Rekommenderad cykelrutt via [Digitransit API](https://digitransit.fi/en/developers/apis/) (kräver en
  gratis API-nyckel).

**TCX** är standardformatet eftersom det låter Strava använda HSL:s exakta sträcka. GPX stöder inte detta.
