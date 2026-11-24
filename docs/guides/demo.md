# M2 demo guide

One end-to-end run through FinSync on synthetic data, for the M2 close (supervisor, [2026-11-23](../planning/supervisor-feedback.md#2026-11-23--reply-to-the-weekly-report-of-nov-1622), priority 3). It shows, in about 15 minutes:

1. A phone notification and the same purchase from a bank export become **one** event.
2. Two purchases of the same amount on the same day stay **two** events.
3. An uncertain match is reviewed, confirmed and undone by splitting.
4. A category is confirmed, corrected, marked mixed and split into lines; the model is asked for one uncertain event (optional).
5. The overview follows every change.

Everything is made up: the group `demo-csalad`, the members `anna` and `balint`, the shops and amounts. The UI is Hungarian; the button names below are quoted as they appear.

## 0. Prepare (5 minutes, once)

From the repository root, with the virtual environment active ([getting started](getting-started.md)):

```bash
python -m finsync.api.demo --db demo.db --export-dir .
```

It refuses an existing file, so delete an old `demo.db` first. It prints:

- the web sign-in: `anna` (admin) or `balint` (member), password `finsync-demo-2026`;
- the path of `demo-bank-export.csv`, dated **today** (seed and run the demo on the same day, Budapest time);
- the API token of the demo phone, shown once. Keep it for step 1.

Then start the API on that database and the web app ([web/README.md](../../web/README.md)):

```bash
python -m finsync.api --db demo.db --host 0.0.0.0     # 0.0.0.0 only when the emulator sends (step 1a)
cd web && npm run dev                                  # second terminal; open http://localhost:5173
```

For step 4's optional model suggestion the server needs `FINSYNC_ANTHROPIC_API_KEY` in its environment; without it everything else works and W8 says that the server has no model.

What the seed contains (W3, "Események"):

| Event | Why it is there |
| --- | --- |
| SPAR, 8 450 Ft | a supermarket the dictionary knows but cannot settle (mixed assortment): a suggestion to confirm |
| BKK AUTOMATA, 1 450 Ft | settled by the dictionary (Közlekedés) |
| TESCO Aruhaz 41021, 12 990 Ft | uncertain, a mixed basket: step 4 |
| SUMUP *KJ BT, 3 200 Ft | a cryptic card-terminal text: uncertain, step 4 (model) |
| MINTA BALINT, 20 000 Ft | a transfer to an own account: listed, left out of the totals |
| MINTA PEKSEG and "Pekseg a sarkon", 2 500 Ft | anna's phone and balint's manual entry of yesterday's bakery purchase: waiting for review, step 3 |

## 1. The same purchase from the phone and from the bank export

Sign in as `anna`. Open **Áttekintés** (W2) and note the total and the event count.

**1a. The phone notification.** With the Android emulator (author, Windows computer, [android-emulator-e2e](../../.claude/skills/android-emulator-e2e/SKILL.md) steps 4–7 with this `demo.db` and the printed token instead of a new one) post case A:

```text
-4 990 Ft erteken vasarolt a PELDABOLT KFT 12. uzleteben.
```

Without the emulator, send the same text as the phone would, from a second terminal (`TOKEN` is the printed token):

```bash
curl -X POST http://127.0.0.1:8080/v1/notifications/ingest \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "{\"message\": \"-4 990 Ft erteken vasarolt a PELDABOLT KFT 12. uzleteben.\", \"posted_at\": \"$(date -Iseconds)\"}"
```

On **Események** (W3) a new event appears: PELDABOLT KFT, 4 990 Ft, source *Értesítés*, its category a suggestion (*Egyéb*, uncertain).

**1b. The bank export.** Open **Importálás** (W7), choose `demo-bank-export.csv` and press **Ellenőrzés**. The column names are recognised; the preview shows three rows and says that nothing is stored yet. Press **3 sor importálása**.

Expected: the result says **"Automatikusan összekapcsolva: 1"** and **"Új esemény: 2"**. The linked row is PELDABOLT: on W3 the PELDABOLT event now has two sources (*Értesítés* and *Fájl*), and it is still one event of 4 990 Ft. Open it (W4): **Források** lists both records, the decision history shows the automatic link.

## 2. Two equal purchases on the same day stay two

The same export has two rows `MINTA KAVEZO`, 1 200 Ft, today, with different bank references. Expected on W3: **two** MINTA KAVEZO events of 1 200 Ft. Two records from the same channel (one export) can never be the same purchase, so the matching engine does not merge them ([matching design](../design/transaction-matching.md)).

## 3. An uncertain match: review, confirm, undo

The side navigation shows one item under **Ellenőrzés** (W5). Open it: yesterday's bakery purchase, anna's phone notification (MINTA PEKSEG, 07:45) against balint's manual entry ("Pekseg a sarkon", day only). Under **Miért kérdezzük?** the screen shows why: same amount (1,00), same day (1,00), merchant text only half alike (0,50), total 0,85, between the review threshold 0.60 and the automatic link at 0.95.

1. Press **Ugyanaz a vásárlás**. The two records become one event; the review counter goes to 0.
2. Open the event (W4). The decision history shows the proposal and anna's confirmation.
3. Undo: at balint's record press **Szétválasztás** and confirm. The record is a separate event again; the history keeps all three steps (proposed, confirmed, split), nothing is overwritten.

(**Két külön vásárlás** on W5 would have kept them apart at once; a rejected pair is never proposed again.)

## 4. Categories: confirm, correct, mixed, lines, model

On W3 tick **Csak bizonytalan kategóriák**: the suggestions nobody settled are listed, each with its source.

1. **One tap.** At SPAR press **✓** next to the suggested *Élelmiszer*: the category is now the member's decision (no "javaslat" mark).
2. **Correct and remember.** Open PELDABOLT KFT (W4). In the category panel choose *Háztartás*, tick **Mindig ezt használd: PELDABOLT KFT** and press **Mentés**. The answer says that a merchant rule was created; it is listed on W8 and applies to new records only.
3. **Mixed and lines.** Open TESCO Aruhaz 41021 (W4). Tick **Vegyes vásárlás**, then **Felosztás kategóriákra**: the editor starts with the whole 12 990 Ft. Enter *Élelmiszer* 9 990 Ft; the last line takes the remainder, set it to *Háztartás* (3 000 Ft). **Mentés**. The lines must add up to the amount, otherwise saving is refused. Supermarkets never get a remembered rule, so the checkbox of step 2 is not offered here.
4. **The model (optional).** Open SUMUP *KJ BT (W4) and press **Kérj javaslatot a modelltől**. At 2 of 5 or more agreeing answers (the threshold 0.40 chosen in the [measurement](../evaluation/results/2026-11-24-categorization-hybrid.md)) the category is settled and shows "N/5 modellválasz egyezett"; otherwise the suggestion stays and the panel says so. A member can still change it. Only the merchant, the description and the amount left the server ([ADR 0013](../architecture/decisions/0013-llm-in-the-live-flow.md)).
5. **History.** Every W4 shows **Kategória-előzmények**: who changed what, when.

On **Beállítások** (W8), the card *Kategória-javaslat nyelvi modellel* shows when the model is asked (*Soha* by default), the month's spending against the budget and, for an admin, the form to change it. Sign in as `balint` to see the same card read-only.

## 5. The overview follows

Back on **Áttekintés** (W2):

- the expense total grew by PELDABOLT once (4 990 Ft, although two records describe it) and by the two coffees (2 × 1 200 Ft); the 20 000 Ft transfer is not in it. While the bakery pair was confirmed (step 3.1) it counted once; after the split it is two events again;
- the Tesco amount is split: 9 990 Ft under *Élelmiszer*, 3 000 Ft under *Háztartás*; PELDABOLT is under *Háztartás*;
- the notice about uncertain categories counts one event (SUMUP, unless the model settled it) instead of four.

Checked on 2026-11-24 by running the same steps through the service on a fresh seed: expenses 31 090 Ft at the start, 38 480 Ft after steps 1–2, 35 980 Ft with the bakery confirmed, 38 480 Ft after the split; uncertain events 3 → 4 (PELDABOLT) → 1.

## If something differs

| What you see | Likely cause |
| --- | --- |
| The PELDABOLT export row is "Új esemény" instead of linked | The notification was not sent before the import, or on another day than the export's date; seed and run on the same day. The order does not matter otherwise: a notification sent after the import joins the event the same way. |
| The seed refuses to run | `demo.db` exists; delete it (it holds only demo data). |
| "Ezt a fájlt már importáltad" on W7 | The export was imported already; reseed for a fresh run. |
| No model button or "nincs beállítva nyelvi modell" | `FINSYNC_ANTHROPIC_API_KEY` is not set for the API process; skip step 4.4. |
| The emulator cannot reach the API | Start the API with `--host 0.0.0.0`; the emulator uses `http://10.0.2.2:8080`. |
