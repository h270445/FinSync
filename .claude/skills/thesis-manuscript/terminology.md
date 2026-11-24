# Hungarian terminology of the thesis

The Hungarian word the manuscript uses for each FinSync concept, the same as the web UI wherever the UI shows it (`web/src/lib/format.ts`, `web/src/components/`). Used by the [thesis-manuscript](SKILL.md) skill; a new term is added here before it appears in a draft. `check_manuscript.py` reads this table: a word in the **Avoid** column found in the manuscript is reported with the term to use (comma-separated; `–` for none).

| English (code, docs) | Hungarian (thesis, UI) | Avoid | Note |
| --- | --- | --- | --- |
| event | esemény | tranzakciócsoport | one purchase, however many records describe it |
| source record, record | forrás, forrásrekord | bejegyzéssor | UI: "Források" on W4 |
| notification | értesítés | – | the bank's push notification on the phone; UI source "Értesítés" |
| bank export, file import | banki export, fájlimport | – | UI: "Importálás" (W7), source "Fájl" |
| manual entry | kézi rögzítés | – | UI source "Kézi" |
| matching | egyeztetés, tranzakció-egyeztetés | párosítás, összefésülés | the matching engine: egyeztető algoritmus |
| duplicate | duplikátum | másolat | the same purchase from two records |
| automatic link | automatikus összekapcsolás | – | UI: "Automatikusan összekapcsolva" |
| review | ellenőrzés | jóváhagyás, review | UI: "Ellenőrzés" (W5) |
| confirm (a match) | megerősítés | – | UI: "Ugyanaz a vásárlás" |
| split (a record off an event) | szétválasztás | leválasztás | UI: "Szétválasztás" |
| reject (a pair) | elutasítás | – | UI: "Két külön vásárlás" |
| decision history | döntési előzmények | – | |
| overview | áttekintés | – | UI: "Áttekintés" (W2) |
| category | kategória | – | |
| suggestion | javaslat, kategória-javaslat | tipp | a category nobody settled; UI: "javaslat" |
| uncertain | bizonytalan | ismeretlen kategória | UI: "Csak bizonytalan kategóriák" |
| mixed purchase | vegyes vásárlás | kevert kosár | UI: "Vegyes vásárlás" |
| category lines | kategóriasorok, felosztás | altételek | UI: "Felosztás kategóriákra" |
| merchant rule | csoportszabály | kereskedőszabály | the group's merchant memory; UI source label "csoportszabály"; "kereskedői szabály" only as an explanation at first use |
| own-account transfer | átvezetés (saját számlák között) | belső utalás | UI: "Átvezetés"; left out of the totals |
| income | bevétel | – | never an uncertain category |
| group, member, admin | csoport, tag, adminisztrátor | háztartás-fiók | |
| API token | API-token | API-kulcs | the phone's long-lived credential |
| web session | webes munkamenet | – | |
| group isolation | csoportok elszigetelése | – | |
| large language model (LLM) | nagy nyelvi modell (LLM) | MI-modell | first use spelled out |
| self-consistency, samples | önkonzisztencia, minták | – | five answers per question |
| threshold | küszöb | – | |
| coverage, accuracy | lefedettség, pontosság | – | |
| dev split, test split | fejlesztési halmaz, teszthalmaz | tanító halmaz | |
| baseline | alapvonal | – | |
| synthetic dataset | szintetikus adathalmaz | – | |
| data minimization | adattakarékosság | – | |
| trust boundary | bizalmi határ | – | |
| agent skill | ügynök-skill (skill) | készség | versioned instructions in `.claude/skills/` |
| architecture decision record (ADR) | architektúra-döntési rekord (ADR) | – | |
