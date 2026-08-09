---
name: hsl-bike-export
description: >-
  Export HSL City Bike (Kaupunkipyörä) ride history into Strava-compatible TCX or GPX files by driving this
  repo's `hsl-kaupunkipyora-exporter` CLI from natural language. Picks the right flags (--format, --linear,
  --use-route, --api-key, --output-dir, --refresh-stations), can fetch the raw ride-history text straight from
  the HSL website when a browser automation tool (Claude in Chrome, chrome-devtools MCP, or Playwright MCP) is
  connected, and reports what was written. Can also offer to upload the resulting files straight to Strava
  using that same browser tool. Trigger on requests like "export my HSL rides", "convert my kaupunkipyörä
  history to Strava", "get my citybike TCX/GPX files", "run the exporter", or "add my Alepa Fillari rides to
  Kilometrikisa".
---

# HSL City Bike ride exporter

You are operating the `hsl-kaupunkipyora-exporter` CLI (this repo) on the user's behalf. It turns an HSL City Bike
ride-history export (HTML save or plain text paste) into per-ride Strava-compatible `.tcx` or `.gpx` files. Your job is
to figure out what the user wants in plain language, get them a valid input file (offering to fetch it yourself via
browser automation when possible), run the CLI, report the result, and — if a browser tool is connected — offer to
upload the resulting files straight to Strava too.

Read this whole file before acting — the steps below are ordered and each depends on the previous one.

## 1. Work out the input file

The CLI needs one local file: either the HTML page saved from the HSL ride-history page, or a plain-text paste of its
visible content. Ask yourself first:

- Did the user already give you a path to such a file (e.g. `rides.txt`, `rides.html`, something in `tcx_output/`
  siblings)? If so, skip straight to step 1d and validate it — do **not** go through 1a-1c, those are only for fetching
  a file you don't already have.
- Did the user instead paste the ride-history text directly into the chat (this is what the README tells people to do —
  copy the visible page text into a `.txt` file)? Write it verbatim to a file yourself (e.g. `rides.txt`) and go
  straight to 1d. Don't offer browser automation or recite the manual steps — they already gave you the data.
- Otherwise, you need to get one. Go to step 1a.

### 1a. Offer to fetch it yourself if a browser tool is connected

Check the current tool/skill listing for any of these — you do **not** need to guess, they show up as available tools or
skills when connected:

- `claude-in-chrome` skill / `mcp__claude-in-chrome__*` tools
- `chrome-devtools-mcp` skill / `mcp__plugin_chrome-devtools-mcp_chrome-devtools__*` tools (or, if configured directly
  rather than as a plugin, `mcp__chrome-devtools__*`)
- `playwright` plugin / `mcp__plugin_playwright_playwright__*` tools (or `mcp__playwright__*` if configured directly)

These patterns cover the common cases, but MCP tool naming isn't fully standardized — a differently-configured host
could expose the same capability under another prefix entirely. If none of the patterns match but you see other tools in
your listing that clearly do browser navigation/page-reading (names involving "browser", "navigate", "page"), treat that
as a connected browser tool too rather than concluding none is available.

If **any** of these is available, offer to grab the page for the user instead of making them do it by hand. Phrase it as
a plain yes/no, not a compound question, so a bare "yes" can't be misread as answering the wrong half:

> "Should I fetch it automatically by opening your HSL ride history page in your browser? You'd need to already be
> logged in to hsl.fi there. (Say no and I'll walk you through saving/pasting it yourself instead.)"

Then **stop and wait for the reply** — do not proceed to 1c in the same turn. If the reply declines (or is just "I'll do
it myself"), go to step 1b.

The user's original request (even something like "I haven't saved anything yet, can you just handle it?") is **not**
consent for this step, no matter how eager it sounds — it's what sent you into 1a in the first place, not a reply to the
offer above. Only an explicit reply to *this specific offer*, made after you've shown it, counts as agreement. If the
reply doesn't clearly say yes to automation (e.g. an ambiguous "yes" that could mean "yes, you do it" or "yes, I'll do
it myself"), ask again rather than assuming. This is the user's personal ride history behind their own login; treat the
browser session as theirs, not something to explore beyond what's needed, and never treat silence or enthusiasm as a
green light.

If **none** of these tools are available, skip the offer entirely and go straight to step 1b (manual path) — don't
mention automation the user has no way to grant you.

### 1b. Manual path (no browser tool, or user prefers to do it themselves)

Tell the user, briefly:

1. Open <https://www.hsl.fi/en/my-information/citybikes/ride-history> (or the `/fi/` or `/sv/` locale — the parser
   understands English, Finnish, and Swedish labels) while logged in.
1. Either save the page as HTML (`Ctrl+S`, "Webpage, Complete") **or** select all the visible ride-history text and
   paste it into a plain `.txt` file.
1. Tell you the path to that file.

Wait for the file before continuing.

### 1c. Fetching it automatically (only after the user agreed in 1a)

1. If it's `claude-in-chrome`: run `ToolSearch` with
   `select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__tabs_create_mcp,mcp__claude-in-chrome__get_page_text,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__computer`
   first (these tools are deferred and unusable until loaded this way — `computer` is included up front because the
   pagination step below needs to click/scroll). Then check `tabs_context_mcp` for an existing hsl.fi tab; otherwise
   open a new tab with `tabs_create_mcp` and `navigate` to
   `https://www.hsl.fi/en/my-information/citybikes/ride-history`. If it's `chrome-devtools-mcp` or `playwright`, the
   equivalent "open/navigate a page" tool is usually called something like `new_page`/`navigate_page` or
   `browser_navigate` — but exact tool names aren't standardized across every way these servers can be configured
   (plugin vs. direct, different hosts), so if the obvious name doesn't exist, use `ToolSearch` with a keyword query
   (e.g. "navigate") to find whatever the connected server actually calls it, rather than assuming.
1. Give the page a moment to load, then check whether you're actually looking at a ride history (not a login wall). If
   it's a login page, stop and tell the user to log in manually in that browser tab, then retry.
1. HSL's ride history can paginate or lazy-load older rides. Before extracting text, look for and use any "load more" /
   "show more" control (find the connected tool's click/scroll equivalent — `computer` for Claude in Chrome, or
   `ToolSearch` for "click"/"scroll" on the others), or scroll to the bottom and wait for new rows to appear, repeating
   until no more rides load or the user only wanted recent ones. If you don't have a tool loaded that can click or
   scroll, or you otherwise can't tell whether more history exists, say so rather than silently exporting a partial
   history.
1. Extract the visible text of the page: `get_page_text`/`read_page` for Claude in Chrome; for chrome-devtools-mcp or
   playwright, prefer their evaluate-script tool (name varies — `ToolSearch` for "evaluate" if unsure) to return
   `document.body.innerText`. Not every connected server exposes script evaluation — some only offer a page
   snapshot/accessibility-tree or "read page" style tool. If there's no evaluate tool, use whatever text-reading tool
   the server does expose instead of getting stuck. Either way, the result should read like
   `tests/test_data/matkahistoria_en.txt` in this repo — repeating blocks of station names, timestamps, distance, and
   duration.
1. Write that text verbatim to a file (e.g. `rides.txt` in the project root, or the scratchpad dir if this isn't a code
   project) with the `Write` tool. Don't reformat or summarize it — the parser needs the raw labeled lines. If you're
   writing it inside a git-tracked project, check it won't be accidentally committed (add it to `.gitignore` if the
   project doesn't already ignore it) — it's the user's personal location history.
1. Tell the user you fetched it and roughly how many rides you found (a quick skim of the text is fine, the CLI will
   give the authoritative count).

### 1d. Validate the file

Before running the CLI, confirm the file exists and isn't empty. If it looks suspiciously short (e.g. a login page's
text, or a page with zero rides), say so and ask the user to double check rather than running the CLI on bad input.

## 2. Work out the CLI options from what the user said

Map natural-language requests to flags. Don't ask about options the user hasn't hinted at — default to the tool's own
sensible defaults (TCX format, summary-only path, `./tcx_output/`) and only add flags when there's a clear signal:

| User says something like...                            | Flag(s)                                              |
| ------------------------------------------------------ | ---------------------------------------------------- |
| "for Strava", "just the distance", nothing specific    | *(defaults: TCX, summary-only)*                      |
| "GPX", with no route/track mentioned                   | ask which path mode first — see warning below        |
| "a straight line on the map", "a rough path"           | `--linear`                                           |
| "the actual route", "follow the streets"               | `--use-route` (needs an API key, see below)          |
| "a map track", "a track I can see on a map"            | `--linear` or `--use-route` — ask which, don't guess |
| "put them in [some other folder]"                      | `--output-dir <path>`                                |
| "refresh/update the station list", stations unresolved | `--refresh-stations`                                 |
| debugging, "what's going wrong", "show me more detail" | `-v` / `--verbose`                                   |

**Warning:** plain `--format gpx` with no path flag writes a GPX file with *zero* track points and no distance override
(GPX has no "reported distance" field — see the TCX-vs-GPX note below) — the ride is a named-but-empty track, and this
failure is invisible until the user opens it in Strava. If the user wants GPX and doesn't mention a path mode, ask
whether they want a straight line (`--linear`) or the real route (`--use-route`) rather than defaulting to a trackless
file.

`--linear` and `--use-route` are mutually exclusive — don't pass both; if the user's phrasing sounds like it wants both
(e.g. "the real route, but a simple map"), ask which one they actually want rather than guessing.

### If `--use-route` is wanted

It needs a Digitransit API key. Check, in order:

1. Is `DIGITRANSIT_API_KEY` already exported in the shell environment you'll run the CLI in? If so, nothing to do — the
   CLI reads it automatically. Note the CLI does **not** load `.env` files itself: a key sitting in a local `.env` only
   counts once it's actually exported into the environment (or you read the file and pass the value via `--api-key`).
1. Did the user give you a key directly? Pass it via `--api-key`.
1. Otherwise, tell the user they need a free key from <https://digitransit.fi/en/developers/api-registration/>, and ask
   if they already have one (paste it) or want to fall back to `--linear`/summary-only for now. Don't fetch or guess a
   key yourself.

## 3. Run the exporter

Prefer running it the way that matches where you are:

- Inside a checkout of this repo (this one, or another clone) with `uv` available:
  `uv run hsl-kaupunkipyora-exporter <file> [flags...]` — this uses the local source, including any uncommitted changes.
- Anywhere else, or if `uv run` isn't set up: `uvx hsl-kaupunkipyora-exporter <file> [flags...]` — this fetches the
  published package, no install needed.
- If neither `uv` nor `uvx` exists on the system, fall back to
  `pip install hsl-kaupunkipyora-exporter && hsl-kaupunkipyora-exporter <file> [flags...]`, but mention you're
  installing something first. This needs Python 3.13+; a system without `uv` is also likely to have an older system
  Python or an externally-managed one that refuses plain `pip install`, so prefer creating a venv with a 3.13+
  interpreter over fighting the system Python.

Run it with Bash, capture stdout/stderr (the CLI logs progress at INFO level: rides found, stations resolved, files
written, any skipped rides and why).

## 4. Report back

Summarize plainly, don't just dump the log:

- How many rides were found and how many files were written, and where (`--output-dir`, default `./tcx_output/`).
- Any skipped rides and why (usually: a station name the lookup couldn't resolve — suggest `--refresh-stations` if
  that's likely stale data).
- A one-line reminder of what format/path-mode was used, if it wasn't the default.
- If this is for Kilometrikisa: the files are meant to be imported into Strava first, then Strava's Kilometrikisa
  integration picks them up — this tool doesn't talk to Strava or Kilometrikisa directly.

If the run failed, read the actual error before guessing — common cases are a missing/invalid input file (step 1's
validation should have caught this), a missing API key for `--use-route`, or a station-list fetch failure. For the last
one: without `--refresh-stations` the CLI uses a local cache and only hits the network if no cache exists yet or the
cache is corrupt, so a network failure there doesn't mean the cache is stale — suggest retrying (or checking
connectivity), not adding `--refresh-stations`, which would just force the same failing download again.

## 5. Offer to upload the result to Strava

Only reachable after step 3 actually wrote files. If a browser tool is connected (same check as step 1a), offer this as
its own separate yes/no — uploading creates real activities on the user's Strava account, and consent for the HSL fetch
does not carry over to a completely different site. Ask something like:

> "Want me to upload the file(s) I just wrote straight to Strava using your browser? You'd need to already be logged in
> there. (Say no and you can drag them into Strava's upload page yourself.)"

Stop and wait for the reply, same rules as step 1a: the user's original export request isn't consent for this either,
even if they clearly meant to end up on Strava (e.g. Kilometrikisa). Only proceed on an explicit yes to *this* offer.

If they agree:

1. Navigate to `https://www.strava.com/upload/select`. Check you're actually logged in (an avatar/name in the top nav,
   not a "Log In" link) before doing anything else — if it's not logged in, stop and tell the user to log in to Strava
   in that browser tab, then retry. This is a separate login from HSL's; don't assume one implies the other.
1. The "File" tab is the default; find its file input (`find` for something like "Choose Files file input") and upload
   the exact file(s) step 3 just wrote — not everything in the output directory, only this run's files — with the
   browser tool's file-upload action. Most of these tools accept multiple files in a single call; Strava's own page also
   accepts multiple `.tcx`/`.fit`/`.gpx` files at once (its own UI states a limit, currently 15 files / 25MB each —
   don't rely on that exact number, read it off the page if it matters).
1. Strava renders one edit form per uploaded file, showing its own parsed distance/duration. Cross-check those against
   what the CLI reported for the same ride as a sanity check that the right files landed on the right activities. Leave
   title, activity type, and privacy at Strava's defaults — don't guess a privacy level or activity type change the user
   didn't ask for; that's their account setting to make, not yours to infer.
1. Find and click "Save & View" (it can appear twice on the page — a duplicate copy in the footer — either works, but
   the one near the form is usually more reliably in view). Scroll it into view first; a click on an element that isn't
   actually in the viewport can silently no-op. Give it a couple of seconds and check that the URL actually changed
   before assuming it saved.
1. Verify by checking `https://www.strava.com/athlete/training_activities?new_activity_only=false` ("My Activities"),
   not just the dashboard feed — the feed can visually bury or de-emphasize one of several activities uploaded in the
   same batch, which reads as a partial failure when it isn't one. Confirm each expected date/distance/time shows up in
   that list before reporting success.

If none of the browser tools are available, skip the offer — same as step 1a, don't dangle a capability the user has no
way to grant.

## Notes

- The parser (`src/hsl_kaupunkipyora_exporter/parser.py`) understands English, Finnish, and Swedish HSL labels, so the
  fetched/pasted text can be in any of those locales — don't translate it.
- `--linear` and `--use-route` only affect the GPS track embedded in the file; TCX also carries HSL's exact reported
  distance/duration regardless of path mode, which is why TCX is the default recommendation over GPX for Strava
  accuracy.
- Never invent or fetch a Digitransit API key on the user's behalf, and never scroll/interact with the user's HSL
  account beyond what's needed to load and read their own ride history.
- Some browser tools restrict `file_upload` to files the user has already "shared with the session" (attachments, an
  outputs/uploads folder, a connected folder) and reject arbitrary paths. If step 5's upload is rejected for that
  reason, say so plainly and ask the user to move the file somewhere the tool can reach, rather than retrying blindly or
  guessing at a different path.
