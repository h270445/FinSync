# 2026-10-28 — Köztes jelzés: a párosítás állása

- Címzett: Dr. Bilicki Vilmos (válasz a 2026-10-16-i levélre)
- Tag: nincs, köztes jelzés (commit: a PR #11 merge-commitja, küldés előtt kitöltendő)
- Státusz: vázlat, küldés 2026-10-28-án este, a vásárlási teszt után

---

**Tárgy:** FinSync szakdolgozat – köztes jelzés a párosítás állásáról

Tisztelt Dr. Bilicki Vilmos!

Köszönöm a válaszát. A javasolt október 22-i köztes jelzést néhány nap késéssel küldöm; elnézést kérek érte, cserébe már az Android-próba első eredményeit is tartalmazza. Röviden: a párosítás működik, megvan az első mérési eredmény, és a technológiai tartaléktervvel éltem.

**A párosítás állása**
- A beérkező feljegyzésekből vásárlási esemény lesz. Mindhárom bemeneti út (értesítés, kézi és tömeges rögzítés) ugyanazon a párosításon megy át egy adatbázis-tranzakcióban; minden döntés (pontszám, jellemzők, szabályverzió) naplózva van, az eredeti adat megmarad.
- A bizonytalan párosítások listázhatók, megerősíthetők és elutasíthatók, a téves összekapcsolás szétválasztható. A közös tétel és az eredeti forrásai lekérdezhetők (`GET /v1/events`). Ez a november 6-ra tervezett végpontokat is tartalmazza, korábban elkészült.
- Az Ön által kiemelt, kézzel eldöntött esetek automatikus tesztként átmennek: ismételt beküldés, fordított érkezési sorrend, csak napra pontos kézi adat, két azonos összegű, de külön vásárlás. A tervezési dokumentum minden párosítási forgatókönyvéhez tartozik egy megnevezett automatikus teszt; jelenleg 62 teszt fut.

**Mérés**
- Elkészült az első, előre eldöntött eredményű, kitalált adathalmaz (100 feljegyzés, 71 vásárlás) és a generátora; a fejlesztési és a végső értékelési példák külön részben vannak.
- Elkészült a kiértékelő futtató és az első eredmények (`docs/evaluation/results/`). Az automatikus összekapcsolás küszöbét csak a fejlesztési részen választottam ki: 0,85 az a legalacsonyabb érték, amelynél ott nincs téves összevonás.
- Az első futtatás után javítottam a bolti nevek összevetésén: a bank által küldött hosszabb név (például „IKEA Budaörs”) és a kézzel beírt „IKEA” korábban csak félig egyezett, most a rövidebb névhez mérem az egyezést.
- A végső értékelési részen, érkezési sorrendben: a minden sort külön tároló alap 12 vásárlást számol kétszer. A párosítás után 1 marad (a javítás előtt 4), és az is ellenőrzésre vár a saját párjával; téves összevonás nincs, a feljegyzések 3,9%-a kerül ellenőrzésre.
- A próbafuttatásban látott hibát (utólag, a rögzítés napjával beírt kézi tétel egy másik, azonos összegű Decathlon-vásárláshoz kapcsolódott) a 0,85-ös küszöb már ellenőrzésre küldi, így a felhasználó elutasíthatja.
- Ismert korlát: fordított érkezési sorrendben egy téves összevonás jelenik meg (két azonos összegű IKEA-vásárlás), mert a párosítás egy feljegyzést nem helyez át, ha később jobb párja érkezik. Ezt vizsgálom a következő lépésben.

**Android-próba**
- Elkészült egy kis próbaalkalmazás (Kotlin), amely csak három bank (OTP Bank, Revolut, K&H) értesítéseit olvassa; minden más alkalmazás értesítését tartalom nélkül eldobja. A rögzített adat a telefonon marad, a repositoryba csak anonimizált formátumleírás kerül.
- Emulátoron, kitalált értesítésekkel már kipróbáltam: többféle értesítésstílus, frissítés ugyanazzal az azonosítóval, törlés, az alkalmazás leállítása és a telefon újraindítása. A legfontosabb tanulság, hogy a figyelő újraindulás után magától visszakapcsol, de a kiesés alatt érkezett értesítéseket az Android nem küldi újra; ezért újracsatlakozáskor a még látható értesítéseket is beolvassa.
- Október 27-én a saját telefonomon (Android 14) megérkezett az első valódi OTP-értesítés egy saját utalásról. Egyetlen szövegmezőben jön az előjeles összeg, a pénznem és a partner neve; időpontot nem tartalmaz, ezért az értesítés rendszeridejét használom, a bank pedig tranzakcióazonosítónak tűnő értéket is küld, ami a duplikátumszűrés kulcsa lehet. Október 28-án egy kártyás vásárlás értesítése is hiánytalanul, egyetlen rekordként érkezett: ugyanazzal az előjeles összeggel és pénznemmel kezdődik, a kereskedő nevét pedig egy mondatban adja meg, így egy OTP-feldolgozó két mintával mindkét fajtát kezeli. A figyelő közben közel egy napig kiesés nélkül futott a telefonon.
- A bankok reklámértesítéseket is küldenek, a Revolut ugyanazon a csatornán, mint a tranzakciókat. Ezért nem a reklámot próbálom felismerni, hanem csak az kerül tovább, ami az adott bank ismert tranzakciómintájára illeszkedik; a többi a telefonon marad, abból csak darabszámot tartok meg. Ha egy banktól napokig nem jön illeszkedő értesítés, az a formátum változására figyelmeztet.

**Két új döntés**
- A Google Sheets-szkript és az Android-alkalmazás egy HTTPS-alagúton (például Cloudflare Tunnel) éri el a gépemen futó API-t, és csak a teszteléshez és a bemutatóhoz indítom el, miután a tokenes hitelesítés elkészült. Állandó szerver így nem kell.
- A csoporton belüli (például családi) átutalás nem költés és nem bevétel: a csoport megadhatja a saját számláit és partnereit, az ezek közötti tételek „pénzmozgatás” típust kapnak, és kimaradnak az összesítésből. Ez az M2 része; a két oldal egy eseménnyé kapcsolását a Szakdolgozat II.-re hagyom.

**Technológia: a tartalékterv**
A tárolás SQLite-on maradt, a FastAPI/PostgreSQL-váltás az M1 után következik. A párosítást a meglévő backendre építettem, mert a november 6-i működő mag a döntő szempont, és a váltás ezt késleltette volna. A párosító logika független a tárolótól, így a váltáskor változatlanul átvihető.

**Az ütemezés a pénteki és szombati munkanapok mellett**
A sorrendet reálisnak tartom: a mag (párosítás és javítás) az első hétvégén elkészült, így a november 6-i határidőig a mérés finomítása és a javítások maradnak, és a belső céldátum (október 30.) előtt tartalék is van. Jelenleg egyik mellékszál sem tűnik túl soknak a novemberi maghoz. Az Android-próba néhány napot csúszott, de nem a mag előfeltétele, ahogy a webes felület váza sem, ezért ha csúsznak, a mérés nem vár rájuk. A közvetlen Google Sheets-szkript továbbra is feltételes. Az Android-próbán a hét elején esténként is dolgoztam, mert a telefonos teszt ezt kívánta; a ráfordított időt a `docs/planning/time-log.md` vezeti. Ha valamelyik szál veszélyeztetné a következő mérföldkövet, időben jelzem.

**Következő lépések (november 6.)**
- Az ismert korlát (fordított érkezési sorrend) vizsgálata, döntés az értesítések időkezeléséről, majd az M1 kiadási jegyzete és címkéje (`v0.2.0`).
- November első hetében a tokenes hitelesítés, amely a csoporttagságot igazolt felhasználóhoz köti, a másik csoport adataihoz való hozzáférés automatikus próbáival.
- A saját döntéseimet és ellenőrzéseimet továbbra is az MI-használati naplóban vezetem.

A repository: https://github.com/h270445/FinSync (commit: `<a PR #11 merge-commitja, küldés előtt kitöltendő>`)

Üdvözlettel:
Varga Bence
