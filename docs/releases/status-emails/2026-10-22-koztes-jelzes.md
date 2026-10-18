# 2026-10-22 — Köztes jelzés: a párosítás állása

- Címzett: Dr. Bilicki Vilmos (válasz a 2026-10-16-i levélre)
- Tag: nincs, köztes jelzés (commit: `23792697efd38d5f61bf56458c1ecaf2e0f45339`)
- Státusz: vázlat

---

**Tárgy:** FinSync szakdolgozat – köztes jelzés a párosítás állásáról

Tisztelt Dr. Bilicki Vilmos!

Köszönöm a válaszát. A javasolt október 22-i köztes jelzést küldöm: a párosítás működik, és a technológiai tartaléktervvel éltem.

**A párosítás állása**
- A beérkező feljegyzésekből vásárlási esemény lesz. Mindhárom bemeneti út (értesítés, kézi és tömeges rögzítés) ugyanazon a párosításon megy át egy adatbázis-tranzakcióban; minden döntés (pontszám, jellemzők, szabályverzió) naplózva van, az eredeti adat megmarad.
- A bizonytalan párosítások listázhatók, megerősíthetők és elutasíthatók, a téves összekapcsolás szétválasztható. A közös tétel és az eredeti forrásai lekérdezhetők (`GET /v1/events`). Ez a november 6-ra tervezett végpontokat is tartalmazza, korábban elkészült.
- Az Ön által kiemelt, kézzel eldöntött esetek automatikus tesztként átmennek: ismételt beküldés, fordított érkezési sorrend, csak napra pontos kézi adat, két azonos összegű, de külön vásárlás. Jelenleg 52 automatikus teszt fut.

**Mérés**
- Elkészült az első, előre eldöntött eredményű, kitalált adathalmaz (100 feljegyzés, 71 vásárlás) és a generátora; a fejlesztési és a végső értékelési példák külön részben vannak.
- Most a kiértékelő futtatón dolgozom: ugyanazon az adaton összeveti a párosítást a minden sort külön tároló alappal, és a téves összevonást külön mutatja. Egy próbafuttatásban már látszott egy tanulságos hiba: a vásárlás napján, utólag rögzített kézi tételt a rendszer egy másik, azonos összegű vásárláshoz kapcsolta. Az ilyen esetekből kiindulva hangolom a küszöböket a fejlesztési részen.

**Technológia: a tartalékterv**
A tárolás SQLite-on maradt, a FastAPI/PostgreSQL-váltás az M1 után következik. A párosítást a meglévő backendre építettem, mert a november 6-i működő mag a döntő szempont, és a váltás ezt késleltette volna. A párosító logika független a tárolótól, így a váltáskor változatlanul átvihető.

**Az ütemezés a pénteki és szombati munkanapok mellett**
A sorrendet reálisnak tartom: a mag (párosítás és javítás) az első hétvégén elkészült, így a november 6-i határidőig a mérés és az első eredmény marad, és a belső céldátum (október 30.) előtt tartalék is van. Jelenleg egyik mellékszál sem tűnik túl soknak a novemberi maghoz. Az Android-próba és a webes felület váza nem a mag előfeltétele, ezért ha csúsznak, a mérés nem vár rájuk. A közvetlen Google Sheets-szkript továbbra is feltételes. Ha valamelyik szál veszélyeztetné a következő mérföldkövet, időben jelzem.

A repository: https://github.com/h270445/FinSync (commit: `23792697efd38d5f61bf56458c1ecaf2e0f45339`)

Üdvözlettel:
Varga Bence
