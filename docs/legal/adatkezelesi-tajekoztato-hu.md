# FinSync – Adatkezelési tájékoztató

**Zárt körű családi tesztüzemhez, az Európai Unió általános adatvédelmi rendelete (GDPR, (EU) 2016/679 rendelet) 13. és 14. cikke alapján**

- Verzió: 0.1 (tervezet)
- Kelt: 2026-11-24
- Hatályos: [KITÖLTENDŐ: hatálybalépés dátuma]

> **Fontos:** ez a dokumentum tervezet, amelyet mesterséges intelligencia segítségével készítettünk, és **nem minősül jogi tanácsadásnak**. Éles használat előtt javasolt ügyvéddel vagy adatvédelmi szakemberrel átnézetni. A [KITÖLTENDŐ] és [ELLENŐRIZENDŐ] jelölésű részeket elfogadás előtt ki kell tölteni, illetve ellenőrizni kell.

## 1. Röviden

- A FinSync a telefonodon megjelenő **OTP Bank vásárlási és utalási értesítéseket** és az általad beírt vagy feltöltött tételeket gyűjti össze, hogy a család közösen lássa a kiadásait.
- Az adatok az Üzemeltető szerverén vannak, a **csoportod minden tagja látja** a csoport összes tételét.
- Banki jelszót, PIN-kódot, kártyaszámot **soha nem kérünk és nem tárolunk.**
- Az **MI-kategorizálás csak a külön hozzájárulásoddal** működik; ekkor tételenként csak a kereskedő neve, a leírás és az összeg megy az Anthropic (USA) szolgáltatásába.
- Bármikor kérheted az adataid **kiadását vagy törlését**, és panaszt tehetsz a NAIH-nál.

## 2. Ki kezeli az adataidat?

**Adatkezelő:** Varga Bence Tamás magánszemély (a továbbiakban: *Üzemeltető*)
E-mail: [KITÖLTENDŐ] · Postacím: [KITÖLTENDŐ]

Adatvédelmi tisztviselő kijelölése nem kötelező (magánszemély, nem nagy léptékű, nem rendszeres megfigyelés).

**Megjegyzés a GDPR alkalmazhatóságáról:** a GDPR nem vonatkozik a természetes személy által kizárólag személyes vagy otthoni tevékenység keretében végzett adatkezelésre (GDPR 2. cikk (2) bekezdés c) pont). A családi tesztüzem valószínűleg ilyen lehet, de ez a körülményektől függ [ELLENŐRIZENDŐ: jogi szakértővel]. Az Üzemeltető ezért úgy kezeli az adataidat, mintha a GDPR teljes egészében vonatkozna rá, és minden jogot megad, amit a GDPR biztosít.

## 3. Milyen adatokat, honnan, miért és milyen jogalapon?

| # | Adatok | Honnan | Cél | Jogalap |
| --- | --- | --- | --- | --- |
| 3.1 | Név vagy becenév (tagazonosító), e-mail-cím, csoporttagság, szerepkör (tag/adminisztrátor) | Az Üzemeltető rögzíti a meghíváskor | Fiók létrehozása, bejelentkezés, jogosultságok | Szerződés teljesítése (GDPR 6. cikk (1) b)) |
| 3.2 | Jelszó (csak sózott, visszafejthetetlen *scrypt* lenyomatként), a webes munkamenet és az API-kulcsok (csak SHA-256 lenyomatként), a kulcs neve, létrehozása, utolsó használata | Te adod meg, illetve a rendszer hozza létre | Biztonságos bejelentkezés, a telefon azonosítása | Szerződés teljesítése (6. cikk (1) b)) |
| 3.3 | **Banki értesítés:** szöveg és cím (összeg, pénznem, kereskedő vagy utalásnál a partner neve, a bank által megjelenített egyéb szöveg), megjelenés időpontja, a bank értesítés-azonosítója, a telefon időzónája | A telefonod, az OTP Bank alkalmazásának értesítései, az Android-alkalmazáson keresztül | A vásárlások automatikus rögzítése, a kettős tételek kiszűrése, utólagos javíthatóság (az eredeti szöveg megőrzése) | Szerződés teljesítése (6. cikk (1) b)) |
| 3.4 | **Kézzel rögzített vagy fájlból importált tételek:** összeg, pénznem, időpont, leírás, kereskedő, kategória, az importfájl neve és sorszáma | Te írod be vagy töltöd fel | Kiadások rögzítése | Szerződés teljesítése (6. cikk (1) b)) |
| 3.5 | **Feldolgozási adatok:** az összepárosítás és kategorizálás eredménye, a döntések naplója (ki, mikor, mit erősített meg, javított vagy bontott szét) | A rendszer és a csoport tagjai | Pontos, ellenőrizhető kiadáskövetés; ki mit módosított | Szerződés teljesítése (6. cikk (1) b)) |
| 3.6 | **Csoportbeállítások:** a csoport saját számlaszámai és utalási partnerei (a családon belüli átutalások felismeréséhez), kereskedő–kategória szabályok | Az adminisztrátor rögzíti | A családon belüli átutalások ne számítsanak kiadásnak | Szerződés teljesítése (6. cikk (1) b)); a nem tag partnerek esetén jogos érdek (6. cikk (1) f)), lásd 4. pont |
| 3.7 | **MI-hívások naplója:** ki kérte, melyik tételhez, felhasznált tokenek, költség | A rendszer | Költségkorlát betartása, visszakereshetőség | Hozzájárulás (6. cikk (1) a)), ugyanaz, mint 3.8 |
| 3.8 | **MI-kategorizálás:** egy tétel kereskedőneve, leírása, összege és pénzneme az Anthropic felé | A tárolt tétel | Kategóriajavaslat kérése | **Külön, önkéntes hozzájárulás** (6. cikk (1) a)), lásd 6. pont |
| 3.9 | Szervernaplók (IP-cím, időpont, kért útvonal, hibakód) és biztonsági mentések | A szerver | Biztonság, visszaélések kiszűrése, hibakeresés, helyreállítás adatvesztés után | Jogos érdek (6. cikk (1) f)): a rendszer és a családtagok adatainak védelme |

**Amit nem kezelünk:** banki belépési adatot, kártyaszámot, egyszer használatos kódot, más alkalmazások értesítéseit (azokat az Android-alkalmazás tartalmuk elolvasása nélkül eldobja), helyadatot, névjegyzéket, és nem banki tranzakciós (pl. reklám) értesítések tartalmát.

**A telefonon maradó adatok:** az Android-alkalmazás a még el nem küldött értesítéseket és a beállításokat (szerver címe, titkosított API-kulcs) a telefon alkalmazás-saját tárhelyén tartja, és csak megszámolja a nem továbbított banki értesítéseket. [ELLENŐRIZENDŐ: a családi változatban a fejlesztői naplózás és az „Export" gomb ki van kapcsolva, a kulcs titkosítva van – felkészülési terv B2.]

### Különleges adatok

A FinSync nem kategorizál egészségügyi, vallási, politikai vagy más különleges adatot (GDPR 9. cikk), és ilyet nem is kér. Egy kereskedő neve (például gyógyszertár, egyházi adomány) azonban következtetni engedhet ilyesmire. Ha egy tételt emiatt nem szeretnél a rendszerben vagy a csoport előtt látni, kérd a törlését (lásd 9. pont), vagy azt a fizetést ne kövesd a FinSyncben.

### Kiskorúak

A FinSync használata 16 éves kor alatt csak a szülő vagy törvényes képviselő hozzájárulásával és jelenlétében történő beállítással lehetséges [ELLENŐRIZENDŐ].

## 4. Harmadik személyek adatai

Utalásnál a banki értesítés tartalmazhatja a **partner nevét**, aki nem feltétlenül tagja a csoportnak. A FinSync ezt a nevet a tétel részeként tárolja, a csoport tagjai látják, és az MI felé soha nem küldi. Jogalap: jogos érdek (6. cikk (1) f)) – a háztartás saját kiadásainak és bevételeinek nyilvántartása; az érintett érdeke kevéssé sérül, mert a név csak a háztartáson belül látszik, és a bank is ugyanígy megjeleníti. A partner kérésére a nevét az Üzemeltető törli vagy kitakarja.

## 5. Kik férnek hozzá az adatokhoz?

| Címzett | Mihez | Miért |
| --- | --- | --- |
| A **csoport többi tagja** | A csoport összes tételéhez, a tagok listájához és szerepköréhez, a csoportbeállításokhoz. API-kulcsokat mindenki csak a sajátját látja. | A közös kiadáskövetés ezt jelenti |
| Az **Üzemeltető** | Üzemeltetőként technikailag minden tárolt adathoz | Üzemeltetés, hibaelhárítás, a 9. pont szerinti kérések teljesítése. Az Üzemeltető az adatokat a szakdolgozatban, mérésekben, nyilvános tárolóban vagy MI-alapú fejlesztőeszközökben **nem használja fel**; ott kizárólag kitalált (szintetikus) adatok szerepelnek. |
| **Tárhelyszolgáltató** (adatfeldolgozó) | A szerveren tárolt adatokhoz, technikailag | A szerver futtatása. Az Európai Unióban bérelt virtuális szerver (VPS). [KITÖLTENDŐ: a szolgáltató neve, székhelye, az adatközpont országa (EU-tagállam)]. Az adatok az EU-ban maradnak. |
| **Anthropic PBC**, San Francisco, USA [ELLENŐRIZENDŐ: pontos cím] (adatfeldolgozó, **csak hozzájárulás esetén**) | Tételenként: kereskedőnév, leírás, összeg, pénznem | Kategóriajavaslat. Lásd 6. pont. |

Az adatokat **nem adjuk el**, reklámcélra nem használjuk, és hatóságnak csak jogszabályban előírt kötelezés alapján adjuk ki.

## 6. MI-kategorizálás – külön hozzájárulás

**Mi történik:** ha a csoportodban az adminisztrátor bekapcsolja (alapértelmezésben **ki van kapcsolva**), a FinSync a még kategória nélküli tételek közül egyenként elküldi a **kereskedő nevét, a leírást, az összeget és a pénznemet** az Anthropic nyelvi modelljének, és kategóriajavaslatot kap vissza. Tagazonosítót, e-mail-címet, számlaszámot, partnernevet vagy más tételt soha nem küld. Egy tag által megadott kategóriát az MI nem ír felül. Csoportonként havi költségkorlát van.

**Adattovábbítás az EU-n kívülre:** az Anthropic az Egyesült Államokban működik. A továbbítás jogalapja [ELLENŐRIZENDŐ az elfogadás napján: az EU–USA adatvédelmi keretrendszer (Data Privacy Framework) szerinti tanúsítás, vagy az Anthropic adatfeldolgozási kiegészítőjében szereplő általános szerződési feltételek (SCC)].

**Az Anthropic adatkezelése:** [ELLENŐRIZENDŐ az elfogadás napján, az Anthropic hatályos kereskedelmi feltételei és adatvédelmi dokumentumai alapján: hogy az API-n küldött adatokat nem használják a modellek tanítására, mennyi ideig őrzik meg, és milyen esetben (például visszaélés-ellenőrzés) tekintenek bele].

**A hozzájárulás önkéntes.** Ha nem adod meg, a FinSync ugyanúgy működik: a kategóriát a csoport szabályai és a beépített szótár adják, a többit a tagok állítják be. A hozzájárulást bármikor, indoklás nélkül visszavonhatod az Üzemeltetőnek írt üzenettel; ezt követően az Üzemeltető a csoportban kikapcsolja a funkciót. A visszavonás nem érinti a korábbi küldések jogszerűségét (GDPR 7. cikk (3)).

Mivel a funkció a csoport összes tételére vonatkozik, **csak akkor kapcsolható be, ha a csoport minden tagja hozzájárult.**

## 7. Meddig tároljuk?

| Adat | Megőrzés |
| --- | --- |
| Fiókadatok, tételek, csoportbeállítások, döntésnapló | A csoporttagság végéig vagy a tesztüzem végéig, majd legfeljebb 30 napon belül törlés |
| A banki értesítés eredeti szövege | [KITÖLTENDŐ, javaslat: 12 hónap], utána az eredeti szöveg törlődik, a feldolgozott mezők (összeg, időpont, kereskedő, kategória) megmaradnak |
| MI-hívások naplója | 12 hónap [KITÖLTENDŐ] |
| Szervernaplók | 30 nap [KITÖLTENDŐ] |
| Biztonsági mentések | Gördülő 30 nap; a törölt adat legkésőbb ennyi idő után a mentésekből is eltűnik [KITÖLTENDŐ] |
| Az elfogadások és hozzájárulások igazolása | A tesztüzem végét követő 5 évig (Ptk. általános elévülési idő), csak az igazoláshoz szükséges adatok |

## 8. Hogyan védjük az adatokat?

- Titkosított kapcsolat (HTTPS) a telefon, a böngésző és a szerver között; a családi változat titkosítatlan kapcsolatot nem enged.
- Jelszavak csak sózott *scrypt* lenyomatként, munkamenetek és API-kulcsok csak SHA-256 lenyomatként tárolva.
- Bejelentkezési süti: `HttpOnly`, `Secure`, `SameSite=Strict`, 12 órás lejárat; minden módosításhoz CSRF-védelem.
- Csoportelkülönítés: minden kérésnél ellenőrzött csoporttagság, automatikus tesztekkel minden végpontra.
- Szerepkörök: a beállításokat csak adminisztrátor módosíthatja; a telefon kulcsa nem tud új kulcsot kiadni.
- A nyelvi modell nem fér hozzá az adatbázishoz, válaszát a rendszer ellenőrzi.
- Napi titkosított mentés [ELLENŐRIZENDŐ: B1].
- Ismert korlát: kétlépcsős azonosítás (MFA) jelenleg nincs; a tesztüzem után, tartós használat előtt bevezetendő.

**Adatvédelmi incidens** esetén az Üzemeltető azt dokumentálja, ha kockázattal jár, 72 órán belül bejelenti a NAIH-nak, magas kockázat esetén téged is haladéktalanul értesít (GDPR 33–34. cikk).

## 9. A jogaid

Az alábbi jogokat az Üzemeltetőnek írt üzenettel gyakorolhatod (2. pont). Az Üzemeltető **egy hónapon belül** válaszol (indokolt esetben ez két hónappal meghosszabbítható, erről értesít), díjmentesen.

- **Hozzáférés** (15. cikk): megtudhatod, milyen adatot kezelünk rólad, és másolatot kérhetsz.
- **Helyesbítés** (16. cikk): a hibás tételeket a webes alkalmazásban magad is javíthatod, a többit az Üzemeltető javítja.
- **Törlés** (17. cikk): kérheted az adataid törlését; a döntésnaplóban a nevedet álnévre cseréljük, hogy a csoport többi tagjának adatai ellenőrizhetők maradjanak.
- **Korlátozás** (18. cikk): vita idején kérheted, hogy az adatot csak tároljuk, de ne használjuk.
- **Adathordozhatóság** (20. cikk): géppel olvasható formában (CSV vagy JSON) kiadjuk a saját adataidat.
- **Tiltakozás** (21. cikk): a jogos érdeken alapuló kezelés (3.6 a partnerek esetén, 3.9, 4. pont) ellen tiltakozhatsz.
- **Hozzájárulás visszavonása** (7. cikk (3)): az MI-kategorizáláshoz adott hozzájárulást bármikor visszavonhatod.
- **Automatizált döntéshozatal** (22. cikk): a FinSync nem hoz rád joghatással járó vagy hasonlóan jelentős, kizárólag automatizált döntést; a párosítás és a kategória csak javaslat, amelyet a csoport tagjai felülbírálhatnak.

**Panasz:** ha úgy érzed, megsértettük a jogaidat, panaszt tehetsz a **Nemzeti Adatvédelmi és Információszabadság Hatóságnál** (NAIH; 1055 Budapest, Falk Miksa utca 9–11.; www.naih.hu) [ELLENŐRIZENDŐ: aktuális elérhetőség], vagy bírósághoz fordulhatsz (a lakóhelyed szerinti törvényszék előtt is). Javasoljuk, hogy előbb az Üzemeltetőnek jelezd a problémát.

## 10. Változások

A tájékoztató módosításáról az Üzemeltető a hatálybalépés előtt legalább 14 nappal értesít. Ha a módosítás új célt vagy új címzettet jelent, ahhoz – ha a jogalap hozzájárulás – újra a hozzájárulásodat kérjük.

## 11. Jogszabályok

- Az Európai Parlament és a Tanács (EU) 2016/679 rendelete (GDPR)
- 2011. évi CXII. törvény az információs önrendelkezési jogról és az információszabadságról (Infotv.)
- 2013. évi V. törvény a Polgári Törvénykönyvről (Ptk.)

---

## Melléklet: hozzájárulás az MI-kategorizáláshoz (önkéntes)

Ez a nyilatkozat **független** a végfelhasználói szerződés elfogadásától. Ha nem írod alá, a FinSyncet ugyanúgy használhatod, csak a csoportodban az MI-kategorizálás nem kapcsolható be.

> Hozzájárulok, hogy a FinSync a csoportom tételei közül a kategória nélkülieknél a kereskedő nevét, a leírást, az összeget és a pénznemet kategóriajavaslat céljából az Anthropic PBC (USA) szolgáltatásának elküldje, a jelen tájékoztató 6. pontjában leírtak szerint. Tudomásul veszem, hogy a hozzájárulásomat bármikor visszavonhatom.

| | |
| --- | --- |
| Név | |
| Dátum | |
| Aláírás | |
| Tájékoztató verziója | 0.1 |
