# Figma prompt plan

- Status: **Proposed**
- Date: 2026-10-09
- Screens and requirements: [user-interface.md](user-interface.md)

Prompts for generating FinSync screens in Figma (Figma Make for clickable prototypes, First Draft in Figma Design for editable layers). Prompts are in English because the tools follow English instructions most reliably; the generated UI text is Hungarian.

## How to use

1. Start every new Figma Make chat or First Draft run with the **base context** below.
2. Add **one screen prompt** at a time. Generating several screens in one prompt gives shallow results.
3. Fix problems with short **iteration prompts** rather than regenerating.
4. Check the result against the **review checklist**, then edit by hand where needed.
5. Log the prompt used and the outcome in the [AI-usage log](../ai-usage.md) (one line per screen batch is enough).

Use only synthetic data in prompts and screens.

## Base context

```text
You are designing screens for FinSync, a shared-expense tracker for couples, families
and roommates. Members of a group send transactions from several sources: banking
notifications forwarded by an Android app, rows from a shared Google Sheet, uploaded
spreadsheet exports and manual entries. FinSync links records that describe the same
purchase into one "event" and asks a member to review uncertain matches. Its key values
are traceability (every event shows where its records came from) and reversibility
(every match decision can be undone).

Constraints:
- Web app, desktop-first (1280 px), must also work at 360 px width.
- All UI text in Hungarian. Amounts in HUF formatted like "12 990 Ft"; dates like
  "2026. 10. 09."; times 24-hour.
- Calm, neutral look: white or light-grey background, one accent colour (teal),
  one warning colour (amber) for "needs review", system font stack, 8 px spacing grid.
- Readable tables, clear focus states, WCAG AA contrast. No dark patterns, no ads,
  no gamification.
- Source badges: "Értesítés" (notification), "Táblázat" (sheet), "Kézi" (manual),
  "Fájl" (file import).
- Use realistic but fictional data: group "Lakás – Fő utca", members "Anna", "Bálint",
  "Csilla"; merchants like "SPAR", "Lidl", "MOL", "Wolt", "BKK".
- Implementation uses React, TypeScript, Tailwind CSS and shadcn/ui components, so
  build from standard components: tables, forms, cards, tabs, dialogs, toasts.
  No complex charts beyond a simple bar chart.
```

## Screen prompts

Prompt order follows the design workflow: low-fidelity first, then one styled screen.

### Step 1: wireframes (low fidelity)

```text
Create greyscale low-fidelity wireframes (no colours, placeholder boxes for icons) for
these three screens, each as a separate frame:
1) "Események" event list (W3)
2) "Ellenőrzés" review queue (W5)
3) Android setup screen (A1)
Use the screen descriptions below. Focus on layout and information hierarchy only.
```

Then paste the descriptions of W3, W5 and A1 from below.

### W3 — Events (Események)

```text
Screen: deduplicated event list for one group and one month.
- Top bar: app name, group switcher, signed-in member, link to settings.
- Left navigation: Áttekintés, Események, Ellenőrzés (with a count badge), Új tétel,
  Importálás, Beállítások.
- Filters row: month picker, member, category, source; a search box for merchant.
- Table columns: date, merchant, category, amount, member, sources (one badge per
  linked record), status. Events waiting for review have an amber "Ellenőrzésre vár"
  tag and a link to the review screen.
- Show 12 example rows; two of them linked from two sources (notification + sheet),
  one waiting for review.
- Clicking a row opens the event detail.
- Mobile: table becomes a card list with date, merchant, amount and badges.
```

### W4 — Event detail (Esemény részletei)

```text
Screen: one event and the records behind it.
- Header: merchant, amount, date and time, category (editable dropdown), status.
- "Források" section: one card per record with source badge, submitting member, received
  time, source reference, import batch id, and a "Nyers adat megjelenítése" toggle that
  reveals the raw payload in a monospace box.
- "Döntési előzmények" timeline: each decision with type (automatikus összekapcsolás,
  megerősítve, elutasítva, szétválasztva), who or which matcher version, when, and score.
- Action: "Szétválasztás" button on each record card, opening a confirmation dialog that
  explains the record will become a separate event.
```

### W5 — Review queue (Ellenőrzés)

```text
Screen: list of uncertain matches, one pair at a time in focus.
- Left: queue list with date, merchant and amount of each pair, and a counter
  ("3 ellenőrzésre vár").
- Right: the selected pair as two cards side by side, each showing source badge,
  member, amount, time, merchant text exactly as received.
- Between or below the cards: a score breakdown with three rows (Összeg, Időpont,
  Kereskedő), each with a small bar, the value and a one-line explanation, e.g.
  "azonos összeg", "4 perc eltérés", "SPAR BUDAPEST vs. Spar".
- Two primary actions: "Ugyanaz a vásárlás" (link) and "Két külön vásárlás" (keep separate).
- After a decision, show a toast with "Visszavonás" (undo).
- Empty state: "Nincs ellenőrzésre váró tétel."
```

### W2 — Overview (Áttekintés)

```text
Screen: month overview for the group.
- Summary cards: total spending this month, change versus last month, events waiting
  for review (amber, links to the review queue).
- Horizontal bar chart of spending per category.
- Small table of spending per member.
- "Legutóbbi események" list with the last 5 events.
```

### W6 — Add transaction (Új tétel)

```text
Screen: manual entry form with fields: amount (HUF), date and time, merchant, description,
category (optional, "automatikus" by default), member (defaults to the signed-in member).
- Inline validation messages in Hungarian (e.g. "Az összegnek pozitívnak kell lennie").
- After saving, show a result panel with the match outcome: new event, linked to an
  existing event (with a link), or sent to review.
```

### W7 — Import file (Importálás)

```text
Screen: three-step import of a spreadsheet export (CSV or XLSX).
1) Upload area with accepted formats and an example column list.
2) Preview table of the first 10 rows with column mapping dropdowns and per-row
   validation errors.
3) Result summary: counts for new events, linked, needs review, re-delivery (skipped),
   and rejected rows with reasons; button to open the review queue.
Explain that the whole file is imported or nothing is ("Az importálás egyben történik").
```

### W8 — Settings (Beállítások)

```text
Screen: group settings with two tabs.
- "Tagok": member list with role.
- "API tokenek": list of tokens with name (e.g. "Anna telefonja", "Közös táblázat"),
  created date, last used, and a "Visszavonás" button. "Új token" opens a dialog that
  shows the token once with a copy button and a warning that it will not be shown again.
```

### W1 — Sign in (Bejelentkezés)

```text
Screen: centered card with e-mail and password fields, a sign-in button and an error
state for wrong credentials.
After sign-in, if the member has several groups, show a group picker.
```

### A1 and A2 — Android app

```text
Android app, Material 3, phone frame 360 x 800, Hungarian text. Two screens:
A1 Setup: server URL field, API token field, "Értesítések elérése" permission row with
status and a button to open system settings, list of supported bank apps with toggles,
"Kapcsolat tesztelése" button with success and error states.
A2 Status: connection status card, last 10 sent notifications (time, amount, merchant,
result: elküldve / ismétlés / hiba), waiting queue count, "Próbaértesítés küldése" button.
The app runs in the background; keep the UI minimal.
```

## Iteration prompts

```text
Keep the layout, but use only one accent colour and make the amber review tag the only warm colour.
```
```text
Make the table denser: 40 px rows, right-aligned amounts, tabular numbers.
```
```text
Show the mobile (360 px) version of this frame next to the desktop one.
```
```text
Replace any English text with Hungarian, keep amounts as "12 990 Ft".
```
```text
Add empty, loading and error states for this screen as separate frames.
```

## Review checklist

- [ ] Every element maps to a field or action in the [API](../guides/api.md) or the [matching design](transaction-matching.md#user-flow-and-api); nothing invented that the backend cannot provide.
- [ ] Sources are visible on every event; review state is visible in lists.
- [ ] Every destructive or linking action has a confirmation or undo.
- [ ] Hungarian text, HUF and date formats are correct.
- [ ] Works at 360 px; contrast is AA.
- [ ] Buildable from shadcn/ui components (no complex custom widgets).
- [ ] Only synthetic data.
