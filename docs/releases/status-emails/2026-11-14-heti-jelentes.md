# 2026-11-14 — Heti jelentés (M2 felé)

- Címzett: Dr. Bilicki Vilmos (válasz a 2026-11-11-i levélre)
- Tag: nincs, heti jelentés (commit: `5f9231fa35e7ff912684d9d8782dd7e83aec5409`, a #28-as pull request utolsó kódváltozása)
- Státusz: vázlat

---

**Tárgy:** FinSync szakdolgozat – heti jelentés (november 9–15.)

Tisztelt Dr. Bilicki Vilmos!

Köszönöm a november 11-i visszajelzését. Ezen a héten a levelében kért M2-pontok közül többet is lezártam; az alábbiakban pontonként írom az állásukat. A párosító motoron, a kérésének megfelelően, nem változtattam.

**Elkészült**

- B1, időkezelés (ADR 0008): az eltolás nélküli időt budapesti helyi időként olvasom, a csak dátummal megadott tétel naptári nap marad, és a napokat budapesti naptár szerint hasonlítom. Az értesítés ideje a telefon által rögzített pillanat (`posted_at`), az érkezés ideje külön tárolódik. Szombaton bekerült az utolsó pont is: a telefon időzónája (`device_zone`) csak diagnosztikai adatként a nyers rekord mellé kerül, a párosítást nem befolyásolja. A harmadik adathalmaz (helyi idővel nyomtatott értesítések) ugyanazokat az eredményeket adja, mint október 29-én.
- B2, PostgreSQL: a tárolás SQLAlchemy Core és Alembic alapon fut SQLite-on és PostgreSQL-en is; a teljes tesztcsomag mindkettőn lefut, a gyors helyi futtatás SQLite-on marad. Docker Compose-zal az adatbázis és az API együtt indítható.
- C1, döntési napló a W4-ben: a `GET /v1/events/{event_id}/decisions` végpont és az esemény részletei oldalon az idővonal (mikor, milyen pontszámmal kapcsolódott, ki erősítette meg, utasította el vagy választotta szét).
- C2 első fele, W6 kézi rögzítés: űrlap magyar ellenőrző üzenetekkel, opcionális budapesti időponttal; mentés után a párosítás eredménye látszik, hivatkozással az eseményre vagy az ellenőrzési listára.
- W1 jelszavas bejelentkezés: e-mail-címmel vagy azonosítóval és jelszóval, HttpOnly session sütivel és CSRF-tokennel (ADR 0010).
- Android-alkalmazás: csak az ismert OTP Bank-minták hagyják el a telefont, kimenő sorral és újrapróbálással, ismétlődés nélkül; az emulátoros végponttól végpontig tartó próba sikeres.
- D1, agentskillek: hét verziózott skill a repositoryban (`.claude/skills/`), használati naplóval a `docs/ai-usage.md`-ben; hogy melyiket mutatom be a módszertani fejezetben, a használat után döntöm el.
- D2, tervezési nézetek: a hat nézetből négy vázlata elkészült Mermaid-diagramként (beérkezés–párosítás–ellenőrzés folyamatábra, esemény- és döntésállapotok, rétegzett architektúra, hitelesítés és csoportizoláció): `docs/architecture/design-views.md`.

**Hogyan ellenőrizhető**

- `python -m unittest discover -s tests` (153 teszt), a webes felületen `npm test` (25 teszt).
- A párosítás mérése a harmadik adathalmazon: `docs/evaluation/results/2026-11-12-matching-rules-3-v3.md`; a végső értékelési részen 0,95-ös küszöbnél mindkét érkezési sorrendben 0 téves összevonás és 64,3% automatikus felismerés, ugyanúgy, mint a második adathalmazon.

**Eltérések a tervtől, kockázatok**

- A) A hibrid kategorizáló tartózkodási küszöbbel még nem készült el; a november 23–27-i hétre tervezem, a lefedettség–pontosság görbével, a késleltetéssel és a költséggel együtt.
- C2 második fele (W7 tömeges import előnézet), C3 (W2 áttekintés) és C4 (W8 beállítások) még nyitott, a következő két hét feladata.
- D2: a use-case diagram és az oldalfolyam (W1–W8, A1–A2) november végén készül, amikor a hátralévő képernyők formája eldőlt; akkor véglegesítem mind a hat nézetet.
- Az Android-továbbítást valódi telefonon még nem próbáltam, csak emulátoron.

**Következő lépések (december 4., M2)**

- W7, W2 és W8, majd a hibrid kategorizáló és a mérése, végül a hat tervezési nézet véglegesítése és a teljes bemutató.
- Ezen a héten (november 9–15.) kb. 5,5 órát dolgoztam a projekten; a részletes időnapló: `docs/planning/time-log.md`.

A repository: https://github.com/h270445/FinSync (commit: https://github.com/h270445/FinSync/commit/5f9231fa35e7ff912684d9d8782dd7e83aec5409)

Üdvözlettel:  
Varga Bence Tamás  
<Neptun-kód>  
Gazdaságinformatikus nappali hallgató
