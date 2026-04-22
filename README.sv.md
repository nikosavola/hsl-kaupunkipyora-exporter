# HSL Kaupunkipyörä Exporter

[![en](https://img.shields.io/badge/lang-en-red.svg)](./README.md)
[![fi](https://img.shields.io/badge/lang-fi-blue.svg)](./README.fi.md)
[![sv](https://img.shields.io/badge/lang-sv-yellow.svg)](./README.sv.md)

Exportera din [HSL-stadscykel](https://www.hsl.fi/sv/mina-uppgifter/stadscyklar/resehistorik)-historik som
Strava-kompatibla TCX- eller GPX-filer.

> För fullständig dokumentation, se [engelska](./README.md) eller [finska](./README.fi.md) versionen.

## Installation

Kräver Python 3.13+.

```bash
uvx hsl-kaupunkipyora-exporter rides.txt
```

## Användning

1. Öppna din resehistorik på <https://www.hsl.fi/sv/mina-uppgifter/stadscyklar/resehistorik>.
1. Spara sidan som HTML (`Ctrl+S`) eller kopiera texten till en `.txt`-fil.
1. Kör verktyget:

```bash
uvx hsl-kaupunkipyora-exporter rides.html
```

## Banlägen

- **Standard**: Endast sammanfattning (exakt sträcka och tid från HSL, inga GPS-punkter).
- `--linear`: Rak linje mellan stationerna.
- `--use-route`: Riktig cykelrutt via [Digitransit API](https://digitransit.fi/sv/utvecklare/apier/) (kräver en gratis
  API-nyckel).

**TCX** är standardformatet eftersom det låter Strava använda HSL:s exakta sträcka. GPX stöder inte detta.
