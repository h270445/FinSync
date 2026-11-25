# 2026-11-25 — M2 zárócsomag, előzetes (v0.3.0)

- Címzett: Dr. Bilicki Vilmos (válasz a 2026-11-23-i levélre)
- Tag: még nincs; a `v0.3.0` tag december 4-én kerül a `main` ágra (commit, a #43 beolvasztása: `1c27c6e132fd879843ea26701740201b9e40bb02`)
- Státusz: elküldve (2026-11-25)

---

**Tárgy:** Szakdolgozat I. - Varga Bence Tamás - <Neptun-kód> - M2 zárócsomag, előzetes (v0.3.0)

**Tisztelt Dr. Bilicki Vilmos!**  
Köszönöm a november 23-i visszajelzését és az ADR 0012 elfogadását. A tervezettnél két nappal korábban elküldöm az M2 zárócsomagot, hogy a december 4-i lezárás előtt legyen idő az észrevételei alapján javítani. A csomag a kiadási jegyzetből (docs/releases/v0.3.0.md), a végigtesztelt `main` ágból és az alábbi összefoglalóból áll. A párosító motoron továbbra sem változtattam.

**Elkészült**
- Hibrid kategorizáló mérése a 200 elemes szintetikus adathalmazon: a csoport szabályai, a magyar szótár, majd az LLM-réteg öt mintával és tartózkodási küszöbbel. A küszöböt (0,40) csak a fejlesztői részen választottam; a teszt részen 79,8% lefedettség mellett a lezárt kategóriák 93,7%-a helyes, a szabályalapú kiindulási módszer 13,1%-os pontosságával szemben. A teljes futás költsége 0,034 USD volt, a hívásonkénti medián késleltetés 0,98 s: docs/evaluation/results/2026-11-24-categorization-hybrid.md.
- LLM az éles folyamatban (ADR 0013, elfogadva): alapértelmezetten kikapcsolva; az ütemezést és a havi költségkeretet csak admin állíthatja a W8 oldalon, webes munkamenetből. A tag egy tételre külön is kérhet javaslatot. A szerverről csak a rekord kereskedője, leírása és összege megy ki, a tag döntését a modell soha nem írja felül, és minden hívás a költségével együtt naplózódik.
- Kategóriajavítás az Ön UX-elvei szerint: a W3 listán és a W4 részleteknél látszik a javaslat forrása és bizonytalansága. Egy koppintással megerősíthető vagy módosítható, a vásárlás „vegyes”-nek jelölhető és az összegre kiegészülő kategóriasorokra bontható, egy tétel átvezetésnek jelölhető. Minden változás naplózódik, és a kereskedő-memória csak nem vegyes kereskedőnél tanul szabályt.
- Egységes bemutató: szintetikus adatokkal feltöltött csoport (python -m finsync.api.demo) és lépésenkénti leírás (docs/guides/demo.md). Ugyanaz a vásárlás telefonos értesítésként és banki táblázatexportból is egy eseménnyé válik, két azonos összegű, aznapi vásárlás viszont kettő marad. A bemutató november 24-én az Android-emulátorral is végigfutott.
- Tervezési nézetek: mind a hat nézetet a kódhoz igazítottam; az 5. és a 6. nézet mutatja az opcionális kimenő modellhívás határát és az adattakarékossági szabályt (docs/architecture/design-views.md).
- D1: a módszertani fejezetbe az Ön javaslatának megfelelően az endpoint-and-screen-checklist (1.2) és a dev-test-evaluation (1.1) skillt választottam. A repositoryban jelenleg tíz verziózott skill van.
- Az M2 elfogadási feltételei bizonyítékokkal a mérföldkő-fájlban: docs/planning/milestones/m2-2026-12-04-integrated-prototype.md.

**Hogyan ellenőrizhető**
- python -m unittest discover -s tests: 275 teszt, mind sikeres SQLite-on; ugyanez PostgreSQL 16-on is lefut (tests/run_on_postgres.py, 10 csak SQLite-ra vonatkozó teszt kihagyva).
- A webes felületen npm test (63 teszt), valamint npm run lint és npm run build, hiba nélkül.
- A két mérés eredménye az eltárolt adatokból újra előállítható: a párosításé python -m finsync.evaluation, a kategorizálásé új LLM-hívás nélkül python -m finsync.evaluation.hybrid.
- A bemutató lépései: docs/guides/demo.md.

**Eltérések a tervtől, kockázatok**
- Vegyes kínálatú kereskedőknél a kategorizálás továbbra is gyenge (a teszt részen 52,4% lefedettség, a lezártak 54,5%-a helyes), a rejtélyes banki szövegek pedig mindig „Bizonytalan”-ok maradnak. A szótár ugyanazokat a nagy láncokat ismeri, mint a szintetikus adathalmaz, ezért az ismert kereskedőkön mért eredmény optimista.
- A helyi modellel való összehasonlítás decemberre marad, ha az idő engedi.
- Az Android A1/A2 szétválasztása az Ön javaslatának megfelelően későbbre került. Az API-token egyelőre sima alkalmazás-beállításban tárolódik.
- A Google Sheets szkript nem készült el; opcionális volt, és a pufferidőben is ez az első, amit elhagyok.
- A sikertelen bejelentkezések korlátozása még hiányzik, ez a decemberi biztonsági értékelés része.

**Következő lépések** (december 4., M2)
- November 26. és december 2. között az Ön észrevételeinek javítása, december 3-án fagyasztás, december 4-én a `v0.3.0` tag és a záró levél.
- Decemberben a magyar kézirat 1–3. fejezetének váza.
- Ezen a héten (november 23–25.) eddig kb. 3,5 órát dolgoztam a projekten; a részletes időnapló: docs/planning/time-log.md.
- A repository: https://github.com/h270445/FinSync (commit: https://github.com/h270445/FinSync/commit/1c27c6e132fd879843ea26701740201b9e40bb02)

**Üdvözlettel:**  
**Varga Bence Tamás**  
<Neptun-kód>  
Gazdaságinformatikus nappali hallgató
