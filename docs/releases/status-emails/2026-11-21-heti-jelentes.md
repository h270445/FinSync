# 2026-11-21 — Heti jelentés (M2 felé)

- Címzett: Dr. Bilicki Vilmos (válasz a 2026-11-16-i levélre)
- Tag: nincs, heti jelentés (commit: `4b107ffb477152ddb92e96cfb4b48b2999c9ca26`, a #35-ös pull request beolvasztása a `main` ágba)
- Státusz: vázlat

---

**Tárgy:** Szakdolgozat I. - Varga Bence Tamás - <Neptun-kód> - Heti jelentés (november 16–22.)

**Tisztelt Dr. Bilicki Vilmos!**  
Köszönöm a november 16-i visszajelzését és az ADR 0010 elfogadását. A levelében kért pontok közül a W2-t, a W8-at és a valódi telefonos Android-próbát lezártam, a hibrid kategorizáló első két rétege pedig a tervezettnél korábban elkészült; az alábbiakban pontonként írom az állásukat. A párosító motoron nem változtattam.

**Elkészült**
- W2 áttekintés (GET /v1/overview): havi, kategóriánkénti és tagonkénti összesítés a duplikátumoktól megtisztított eseményekre építve; a csoporton belüli átvezetések kimaradnak, az ellenőrzésre váró tételek külön jelölve látszanak.
- W8 beállítások: tagok admin és tag szerepkörrel (csoportbeállítást csak admin módosíthat), saját API-tokenek létrehozása és visszavonása csak webes munkamenetből, csoportszintű kereskedő → kategória szabályok, és a csoport saját számlái, amelyek alapján az átvezetés `transfer` irányt kap, és nem számít kiadásnak.
- Hibrid kategorizáló, determinisztikus réteg: a csoport szabályai alatt beépített magyar kereskedő- és kulcsszószótár (96 kereskedő, 179 kulcsszó, például SPAR, MOL, MÁV-START, dm), amely minden új rekordnál fut; a vegyes kínálatú kereskedőknél csak alacsony biztonságú javaslatot ad. A szótárt általános ismeretek alapján írtam, nem a címkézett adathalmazból.
- Hibrid kategorizáló, LLM-réteg (ADR 0011): rekordonként öt válasz, a leggyakoribb kategória aránya a megbízhatóság; a küszöb alatt a tétel „Bizonytalan” marad. A mérőprogram a küszöböt csak a fejlesztői részen választja, a teszt részt egyszer futtatja, és költségbecslést ad fizetős hívás előtt.
- Valódi telefonos Android-próba (Samsung Galaxy A13, Android 14): az emulátoros esetek kitalált értesítésekkel, majd egy valódi OTP Bank-kártyás vásárlás; a telefon felismerte és elküldte, a szerveren pontosan egy esemény lett belőle, ismétlődés nélkül. Az értesítés szövegét a próba során nem olvastam ki. A próba egy hibát is mutatott (hosszú szerverleállás után az azonnali küldés gomb órákig várt az újrapróbálásra), ezt javítottam és a telefonon ellenőriztem.
- ADR 0012 (javaslat): többfaktoros hitelesítés nem része a szakdolgozatnak, mert a rendszer pénzt nem mozgat, a telefon pedig tokennel azonosít; következő lépésként érzékeny műveleteknél újbóli jelszókérést javaslok, a sikertelen bejelentkezések korlátozása a decemberi biztonsági értékelésbe kerül.
- D2: az 1–2. tervezési nézet (use-case, oldalfolyam W1–W8 és A1–A2) vázlata elkészült a megépült képernyők alapján: docs/architecture/design-views.md.

**Hogyan ellenőrizhető**
- python -m unittest discover -s tests (242 teszt), a webes felületen npm test (43 teszt).
- A telefonos próba eredménye: docs/design/android-notification-spike.md („2026-11-20–21: M2 forwarding on the real phone” rész).
- A hibrid mérés futtatási leírása: docs/evaluation/hybrid-measurement-runbook.md.

**Eltérések a tervtől, kockázatok**
- A hibrid kategorizáló mérése még nem futott: a fizetős LLM-futtatáshoz szükséges API-kulcs a november 23-i héten érkezik; a lefedettség–pontosság görbét, a késleltetést és a költséget a jövő heti jelentésben küldöm.
- Az LLM-réteg egyelőre csak a mérésben fut; a rekord mentésekor még nem hívódik meg.
- D1: a módszertani fejezetben bemutatott skill(ek)ről a jövő heti mérés után döntök, az Ön javaslatának megfelelően a dev-test-evaluation skillt is figyelembe véve.
- A magyar kézirat (1–3. fejezet) vázát decemberben kezdem el.

**Következő lépések** (december 4., M2)
- A hibrid kategorizáló mérése és bekötése a rekordmentésbe, kategóriajavítás a „vegyes” jelöléssel, a hat tervezési nézet véglegesítése, végül a teljes bemutató.
- Ezen a héten (november 16–22.) kb. 2,8 órát dolgoztam a projekten; a részletes időnapló: docs/planning/time-log.md.
- A repository: https://github.com/h270445/FinSync (commit: https://github.com/h270445/FinSync/commit/4b107ffb477152ddb92e96cfb4b48b2999c9ca26)

**Üdvözlettel:**  
**Varga Bence Tamás**  
<Neptun-kód>  
Gazdaságinformatikus nappali hallgató
