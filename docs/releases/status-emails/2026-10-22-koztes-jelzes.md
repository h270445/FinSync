# 2026-10-22 — Köztes jelzés: a párosítás állása

- Címzett: Dr. Bilicki Vilmos (válasz a 2026-10-16-i levélre)
- Tag: nincs, köztes jelzés (commit: `d7c3a0bb593f2e66270bfcfb70d93509e02294eb`)
- Státusz: vázlat

---

**Tárgy:** FinSync szakdolgozat – köztes jelzés a párosítás állásáról

Tisztelt Dr. Bilicki Vilmos!

Köszönöm a válaszát. A javasolt október 22-i köztes jelzést küldöm: a párosítás működik, megvan az első mérési eredmény, és a technológiai tartaléktervvel éltem.

**A párosítás állása**
- A beérkező feljegyzésekből vásárlási esemény lesz. Mindhárom bemeneti út (értesítés, kézi és tömeges rögzítés) ugyanazon a párosításon megy át egy adatbázis-tranzakcióban; minden döntés (pontszám, jellemzők, szabályverzió) naplózva van, az eredeti adat megmarad.
- A bizonytalan párosítások listázhatók, megerősíthetők és elutasíthatók, a téves összekapcsolás szétválasztható. A közös tétel és az eredeti forrásai lekérdezhetők (`GET /v1/events`). Ez a november 6-ra tervezett végpontokat is tartalmazza, korábban elkészült.
- Az Ön által kiemelt, kézzel eldöntött esetek automatikus tesztként átmennek: ismételt beküldés, fordított érkezési sorrend, csak napra pontos kézi adat, két azonos összegű, de külön vásárlás. Jelenleg 61 automatikus teszt fut.

**Mérés**
- Elkészült az első, előre eldöntött eredményű, kitalált adathalmaz (100 feljegyzés, 71 vásárlás) és a generátora; a fejlesztési és a végső értékelési példák külön részben vannak.
- Elkészült a kiértékelő futtató és az első eredmények (`docs/evaluation/results/`). Az automatikus összekapcsolás küszöbét csak a fejlesztési részen választottam ki: 0,85 az a legalacsonyabb érték, amelynél ott nincs téves összevonás.
- Az első futtatás után javítottam a bolti nevek összevetésén: a bank által küldött hosszabb név (például „IKEA Budaörs”) és a kézzel beírt „IKEA” korábban csak félig egyezett, most a rövidebb névhez mérem az egyezést.
- A végső értékelési részen, érkezési sorrendben: a minden sort külön tároló alap 12 vásárlást számol kétszer. A párosítás után 1 marad (a javítás előtt 4), és az is ellenőrzésre vár a saját párjával; téves összevonás nincs, a feljegyzések 3,9%-a kerül ellenőrzésre.
- A próbafuttatásban látott hibát (utólag, a rögzítés napjával beírt kézi tétel egy másik, azonos összegű Decathlon-vásárláshoz kapcsolódott) a 0,85-ös küszöb már ellenőrzésre küldi, így a felhasználó elutasíthatja.
- Ismert korlát: fordított érkezési sorrendben egy téves összevonás jelenik meg (két azonos összegű IKEA-vásárlás), mert a párosítás egy feljegyzést nem helyez át, ha később jobb párja érkezik. Ezt vizsgálom a következő lépésben.

**Technológia: a tartalékterv**
A tárolás SQLite-on maradt, a FastAPI/PostgreSQL-váltás az M1 után következik. A párosítást a meglévő backendre építettem, mert a november 6-i működő mag a döntő szempont, és a váltás ezt késleltette volna. A párosító logika független a tárolótól, így a váltáskor változatlanul átvihető.

**Az ütemezés a pénteki és szombati munkanapok mellett**
A sorrendet reálisnak tartom: a mag (párosítás és javítás) az első hétvégén elkészült, így a november 6-i határidőig a mérés finomítása és a javítások maradnak, és a belső céldátum (október 30.) előtt tartalék is van. Jelenleg egyik mellékszál sem tűnik túl soknak a novemberi maghoz. Az Android-próba és a webes felület váza nem a mag előfeltétele, ezért ha csúsznak, a mérés nem vár rájuk. A közvetlen Google Sheets-szkript továbbra is feltételes. Ha valamelyik szál veszélyeztetné a következő mérföldkövet, időben jelzem.

A repository: https://github.com/h270445/FinSync (commit: `d7c3a0bb593f2e66270bfcfb70d93509e02294eb`)

Üdvözlettel:
Varga Bence
