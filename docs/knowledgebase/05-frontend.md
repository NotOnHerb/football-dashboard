# 05 — Front end (`template.html`, `analyst/desk.html`)

## Shape

- **One file**, vanilla JS (mostly ES5), no framework, no modules, no build step. The only external resource is Google Fonts.
- `template.html` (1,154 lines, ~198 KB):

| Part | Lines | Size |
|---|---|---|
| CSS | 7-166 | ~19 KB |
| HTML skeleton (every section is static markup) | 167-217 | ~13 KB |
| JS (one inline `<script>`) | 218-1155 | ~165 KB, ~194 named functions, ~30 top-level state objects |
| …animated canvas backgrounds (`SC`: ocean/grass/snow) | 219-266 | ~9 KB |
| …glossary data (`GL`/`GLR`/`GLC`) | 755-764 | ~16 KB (line 755 alone is 12 KB) |

- **Boot** (`load()`, line 1143): fetch `data.json?v=__VER__`, then run 14 init functions in one chain (line 1152):
  `wire(); renderP(); renderT(); initN(); cInit(); initX(); initD(); initC(); initF(); initGloss(); initFM(); initCards(); initB(); …`

## Section map

Top-level tabs are **NFL / Fantasy / Betting** (`#sec` at line 170, mirrored in the mobile bottom nav `#bnav` at line 216, switched by `showSec` at 466).

| Section → view | Render functions | `data.json` keys | Lines |
|---|---|---|---|
| NFL → Teams | `renderT` → `teamTbl`; `team()`, `mixBar` | T, TC, N | 298-345 |
| NFL → Players (off/def/OL) | `render` → `renderP` / `renderX` / `renderOL`; `colsFor`, `tbl`, `cell` | P, PC, X, OLP | 272-297, 441-459 |
| NFL → Matchups | `initN`, `matchup`, `side`, `olTable`, `meter`; `skillRender`, `skillSide` | G, T, X, DEP, ALW | 350-415 |
| NFL → Compare | `cInit`, `cSetup`, `cRender` | P, PC | 416-440 |
| Fantasy → My league | `fSleeper`, `fEspn` → `leagueRender` → `sRender` (dynasty) / `fRender` (redraft), `lineupHTML`, `tFind`, `fWaiver` | DY.L/K/E, ALW, G, PRI | 551-608, 656-741 |
| Fantasy → Start/sit | `renderF`, `renderMy`, `wkPts`, `bestLineup` | P, ALW, G, PRI, DY.L | 609-646, 699-710 |
| Fantasy → Rankings (dynasty) | `renderD`, `dRows`, `why` | DY.P, DY.K | 469-507 |
| Fantasy → College | `renderC`, `renderBB`, `initC` | CF | 508-550 |
| Betting → Picks / Games / Props | `renderB` → `picks`, `pickCard`, `gameCard`, `propTable`, `parlayHTML`, `comboHTML`, `movesHTML` | ODD.* | 900-1050, 1098-1122 |
| Betting → My bets / Results | `mineView`, `gradeBet`, `resultsView` | ODD.FIN, ODD.LG, LOG, localStorage | 994-1028 |
| Betting → College | `collegeView`, `cfPickCard`, `cfGameCard`, `cfBest`, `cfbResults` | CFB | 1051-1097 |
| Player card (modal) | `openCard`, `cardNews`, `logChart` | PL, LOG, DY.P, ODD.P, P, X | 806-858 |
| Cross-cutting | `gloss` (tooltips), `colorize` (heat colors), `reSort` (sorting), run after every render by a `MutationObserver` on `<main>` (802) | | 765-805 |

"Dynasty" is a format toggle inside Fantasy (`FMT`), not a tab. "College" appears in both Fantasy (prospects) and Betting (lines).

## State

- **Globals:** `D` (the whole dataset), `A`, `st`, plus ~27 per-section state objects (`OS`, `TS`, `DS`, `CS`, `FS`, `BS`, `CBS`, …).
- **localStorage keys (12, no namespace):** `scene`, `theme`, `motion`, `colors`, `fmt`, `blg`, `book`, `mybets`,
  `sleeper_user`, `espn_league`, `espn_team`, `last_league`. The **My bets** slip lives only here, per browser.
- **No routing.** Nothing references `location`, `history` or `hashchange`. A reload always lands on NFL → Teams, and views can't be deep-linked.
- **Events** use a mix of patterns: delegation on `data-*`, direct `.onclick`, two inline handlers, document-level and
  capture-phase listeners. The visual and a11y state is `aria-pressed`, re-synced by hand.
- **Shared data is mutated in place.** `setSc` (462) rewrites player rows and `D.PC` labels when the scoring format changes,
  then calls five other sections' renderers.

## Runtime calls from the browser

| Call | Purpose | Line |
|---|---|---|
| `data.json` | Everything | 1145 |
| `api.sleeper.app/v1/…` | Sleeper user, leagues, rosters, traded picks | 553 |
| `lm-api-reads.fantasy.espn.com/…` | ESPN fantasy league | 683 |
| `site.web.api.espn.com/…/athletes/{id}/overview` | Player news | 844 |
| headshot URLs from `D.PL` | Images | 827 |

The page does not fetch `odds/*.json`. Weather is pre-baked into `ODD.G[].ctx.wx`.

## Business logic in the browser

- **The pick engine runs twice.** The page **never reads `ODD.PK`** (build.py's official picks). It recomputes picks on
  every Betting render with hand-copied versions of `valS`, `gq`, `gfair`, `gev`, `gside`, `pq`, `pOver`, `ptier`, `pa` and `picks`
  (template.html:873-936 ↔ build.py:655-763). Only the thresholds are shared, via `D.ODD.RU`. Known differences:
  - Fallback rules when `ODD.RU` is missing lack `tdmax`, which zeroes every TD lean (873).
  - The page supports a single-book filter.
  - The page uses the **viewer's clock** for "already started"; build.py uses build time.
- **Grading twice.** `gradeBet` (1003) grades My bets in the browser; `grade_one` (build.py:895) grades the ledger.
- **Projection** `fbase` (813) re-implements 85/15 + prior. The matchup factor appears three times (639, 703, 815).
  There are two grade scales (`grade` 611, `bgrade` 877). PPR/Half/Std blending is repeated in about 8 places.
- **Fantasy logic** lives only in the browser: lineup optimizer `bestLineup` (705), dynasty power rankings and buy/sell
  (`sRender` 555-603), trade finder `tFind` (604), waivers (730), "diamonds" (494).

## Code-quality notes

- Names are mostly 1-2 letters. There's some shadowing (local `ord`, `f`, `rec` vs functions of the same name) and some
  duplicate helpers (`ord`/`nth`, `LOWER`/`LOWB`).
- Largest functions: `sRender` 9.8 KB, `renderC` 5.5 KB, `renderB` 5.1 KB, `openCard` 4.1 KB, `fRender` 4.0 KB.
- **Escaping is inconsistent: 65 `innerHTML` writes against 14 `esc()` calls.**
  - ESPN news is escaped.
  - Sleeper league and team names escape only `<`.
  - ESPN roster names, Odds API player names and big-board URLs (in `href`) go in raw.

  Sleeper and ESPN team names are typed by other league members, so this is the one real injection path today.
- **No per-section error isolation.** One missing key in the init chain stops every later section from loading.
- **Dead code:** `renderTB`/`TB` (346), `KC` (443), branches at 446, 488, 620. References to non-existent `D.K` and `D.OL`.
- **Accessibility shows clear intent.** It has many `aria-pressed`/`aria-label` attributes, keyboard sorting, Escape to
  close the modal with focus restore, and focus-visible styles. Missing: a focus trap, tablist roles, a loading live region.
- **Mobile is handled deliberately:** 420/600 px breakpoints, bottom nav, sticky first column, safe-area insets, motion
  off on phones.
- **Performance:**
  - All 1.33 MB is parsed before first paint.
  - Every section renders eagerly at boot.
  - Every filter keystroke rebuilds a whole table, and then the observer walks every cell.

## `analyst/desk.html`

- A Claude Artifact using `claude.use('db' | 'user' | 'sample')`. Tabs: This week, Proposals, Ask, Ideas, Picks, Notebook.
  It **has hash routing**, unlike the main page.
- Reads `snap/*`, `reports`, `notebook`. The owner can approve or pass proposals (two-tap write). It can add ideas, and it
  persists `chat/history`.
- **Ask tab** = an LLM call with a `RULES` prompt and 10 tools over the in-memory snapshot (`overview`, `current_picks`,
  `pick_log`, `player_props`, `game`, `best_edges`, `reports`, `proposals`, `ideas_and_notebook`, `add_idea`).
  **This is the most complete agent tool surface in the project**, and it only exists inside the Artifact.
- `RULES` restates the model thresholds in prose, which makes a fourth copy of the pick rules. Escaping is consistent here.

## Cost to add a new section today

A new top-level module currently touches about 8 places:
- static HTML;
- both nav bars (`#sec` and `#bnav`);
- `showSec`'s hide list;
- the init chain;
- a new global state object;
- the `aria-pressed` sync loops;
- the `setSc` fan-out (if it shows points);
- the glossary / header-text lists.

It also needs coordinated edits to positional arrays in `build.py`.
