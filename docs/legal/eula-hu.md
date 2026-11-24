# FinSync – Végfelhasználói licencszerződés (EULA)

**Zárt körű, ingyenes családi tesztüzemhez**

- Verzió: 0.1 (tervezet)
- Kelt: 2026-11-24
- Hatályos: [KITÖLTENDŐ: hatálybalépés dátuma]

> **Fontos:** ez a dokumentum tervezet, amelyet mesterséges intelligencia segítségével készítettünk, és **nem minősül jogi tanácsadásnak**. Éles használat előtt javasolt ügyvéddel vagy adatvédelmi szakemberrel átnézetni. A [KITÖLTENDŐ] és [ELLENŐRIZENDŐ] jelölésű részeket elfogadás előtt ki kell tölteni, illetve ellenőrizni kell.

## 1. A szerződő felek

1.1. **Üzemeltető:** Varga Bence Tamás magánszemély, a FinSync szoftver szerzője és a FinSync szerver üzemeltetője (a továbbiakban: *Üzemeltető*).
Elérhetőség: [KITÖLTENDŐ: e-mail-cím], [KITÖLTENDŐ: postacím].

1.2. **Felhasználó:** az a természetes személy, akit az Üzemeltető személyesen meghívott a zárt körű tesztbe, és aki ezt a szerződést elfogadja (a továbbiakban: *Felhasználó*).

1.3. A szerződés ingyenes. Sem a Felhasználó, sem az Üzemeltető nem fizet a másiknak semmit.

## 2. Fogalmak

- **FinSync:** kiadáskövető rendszer, amely egy közös csoport (például egy család) tagjainak kiadásait gyűjti össze, a több forrásból érkező, ugyanarra a vásárlásra vonatkozó tételeket összepárosítja, és kategóriákba sorolja. Részei: az Android-alkalmazás, a webes alkalmazás és a szerver.
- **Android-alkalmazás:** a Felhasználó telefonjára telepített FinSync alkalmazás, amely a támogatott bank (jelenleg kizárólag az OTP Bank) alkalmazásának értesítéseiből a vásárlásokat a szerverre továbbítja.
- **Webes alkalmazás:** böngészőből elérhető felület, ahol a Felhasználó a csoport tételeit látja, javítja és rögzíti.
- **Szerver:** az Üzemeltető által működtetett számítógép, amely az adatokat tárolja és feldolgozza.
- **Csoport:** a FinSyncben együtt követett háztartás vagy család. A csoport minden tagja látja a csoport összes tételét.
- **Adminisztrátor:** a csoport olyan tagja, aki a csoport beállításait (kereskedő–kategória szabályok, saját számlák, szerepkörök, MI-ütemezés) módosíthatja.
- **MI-kategorizálás:** opcionális funkció, amely egy tétel kereskedőnevét, leírását és összegét az Anthropic nyelvi modelljének elküldve kategóriajavaslatot kér.
- **Tesztüzem:** az a zárt körű, időben korlátozott használat, amelyre ez a szerződés vonatkozik.

## 3. A szerződés tárgya és a licenc

3.1. Az Üzemeltető a szerződés időtartamára a Felhasználónak **ingyenes, nem kizárólagos, nem átruházható, harmadik személynek tovább nem adható, bármikor visszavonható** felhasználási jogot ad arra, hogy

a) az Üzemeltetőtől kapott Android-alkalmazást a saját telefonjára telepítse és használja;
b) a webes alkalmazást a saját fiókjával használja;
c) a szerver szolgáltatásait a saját csoportja keretében igénybe vegye.

3.2. A felhasználási jog **kizárólag magáncélú, háztartási használatra** szól. Üzleti, munkahelyi vagy mások számára végzett könyvelési célra nem használható.

3.3. A FinSync forráskódja az MIT-licenc alatt nyilvános. Ez a szerződés a forráskód MIT-licenc szerinti felhasználását nem korlátozza; kizárólag az Üzemeltető által futtatott szerver, a Felhasználó fiókja és adatai, valamint az Üzemeltető által átadott alkalmazásváltozat használatára vonatkozik.

3.4. A FinSync szellemi tulajdonjogai az Üzemeltetőnél maradnak, a felhasznált nyílt forráskódú összetevők jogai azok jogosultjainál.

## 4. Tesztjelleg

4.1. A FinSync egy egyetemi szakdolgozati projekt (Szegedi Tudományegyetem) keretében készülő **prototípus**. A Felhasználó tudomásul veszi, hogy

a) a szoftver hibákat tartalmazhat, a tételek kimaradhatnak, kétszer szerepelhetnek, rosszul párosodhatnak vagy rossz kategóriába kerülhetnek;
b) a szerver nem éjjel-nappal felügyelt, karbantartás vagy hiba miatt órákig vagy napokig elérhetetlen lehet;
c) az Üzemeltető a funkciókat bármikor módosíthatja, szüneteltetheti vagy megszüntetheti;
d) a tesztüzem időben korlátozott; az Üzemeltető legalább 14 nappal a vége előtt értesíti a Felhasználót.

4.2. A FinSync **nem helyettesíti** a bank hivatalos számlakivonatát. Vita, reklamáció, adóügy vagy bármilyen hivatalos ügy esetén mindig a bank adatai az irányadók.

4.3. A Felhasználó kéri, hogy hibát vagy furcsaságot jelezzen az Üzemeltetőnek. A visszajelzéseket az Üzemeltető a szoftver javítására használhatja.

## 5. Mit nem csinál a FinSync

5.1. A FinSync **nem banki és nem pénzügyi szolgáltatás.** Nem indít fizetést, nem fér hozzá a Felhasználó bankszámlájához, és nem kér, nem tárol banki belépési adatot (felhasználónevet, jelszót, PIN-kódot, kártyaszámot, egyszer használatos kódot).

5.2. A FinSync **nem ad pénzügyi, befektetési, adó- vagy jogi tanácsot.** A kategóriák, összesítések és MI-javaslatok csak tájékoztató jellegűek.

5.3. Az Üzemeltető soha nem kér a Felhasználótól banki belépési adatot. Ha valaki a FinSync nevében ilyet kér, az csalás; a Felhasználó jelezze az Üzemeltetőnek.

## 6. Az Android-alkalmazás és az értesítésekhez való hozzáférés

6.1. Az Android-alkalmazás működéséhez a Felhasználónak a telefon beállításaiban **értesítés-hozzáférést** kell adnia. Ezzel az Android technikailag minden alkalmazás értesítését eljuttatja a FinSynchez. Az alkalmazás

a) a nem banki alkalmazások értesítéseit azonnal, tartalmuk elolvasása és tárolása nélkül eldobja;
b) a támogatott bank értesítései közül csak azokat küldi a szerverre, amelyek ismert vásárlási vagy utalási formátumúak;
c) minden más banki értesítést (például reklám, hír) a telefonon csak megszámol, nem továbbít.

6.2. Továbbított adatok értesítésenként: az értesítés szövege és címe, a megjelenés időpontja, a bank által adott azonosító és a telefon időzónája. A részleteket az [Adatkezelési tájékoztató](adatkezelesi-tajekoztato-hu.md) írja le.

6.3. Az értesítés-hozzáférés a telefon beállításaiban bármikor visszavonható; ekkor a FinSync nem kap új tételt.

6.4. A Felhasználó csak a **saját** telefonjára és a **saját** bankszámlájának értesítéseire telepítheti és használhatja az alkalmazást. Más személy telefonjára az ő tudta és elfogadása nélkül tilos telepíteni.

6.5. Az alkalmazást a Felhasználó kizárólag az Üzemeltetőtől személyesen vagy általa megadott módon kapott, aláírt telepítőcsomagból telepítse. Ismeretlen forrásból származó „FinSync" alkalmazást ne telepítsen.

## 7. Fiók, jelszó, hozzáférési kulcs

7.1. A Felhasználó fiókját az Üzemeltető hozza létre. A kezdő jelszót a Felhasználó az első bejelentkezés után köteles megváltoztatni [ELLENŐRIZENDŐ: a jelszócsere funkció elkészülte, lásd a felkészülési terv B3 pontját].

7.2. A Felhasználó köteles a jelszavát és a telefonon tárolt hozzáférési kulcsot (API-tokent) titokban tartani, mással meg nem osztani, és egyedi, máshol nem használt jelszót választani.

7.3. Ha a Felhasználó telefonja elveszik, vagy azt gyanítja, hogy illetéktelen fér hozzá a fiókjához, haladéktalanul értesíti az Üzemeltetőt, illetve a webes alkalmazásban visszavonja a telefon kulcsát.

7.4. A fiókon keresztül végzett műveletekért – az Üzemeltető hibáját kivéve – a Felhasználó felel.

## 8. A csoporton belüli láthatóság

8.1. A csoport **minden tagja látja a csoport összes tételét**: összeget, kereskedőt, időpontot, kategóriát, a forrást és – utalásnál – a partner nevét, ha a banki értesítés tartalmazza. A Felhasználó ezt a csatlakozással tudomásul veszi.

8.2. Ha a Felhasználó valamelyik kiadását nem szeretné megosztani a csoporttal, ne használja a FinSyncet arra a számlára vagy kártyára, illetve kérje a tétel törlését az Üzemeltetőtől.

8.3. Az adminisztrátorok a csoport beállításait módosíthatják. Más tagok tételeit egy adminisztrátor sem rejtheti el a többiek elől, és egyetlen tag sem látja más csoport adatait.

## 9. MI-kategorizálás (opcionális)

9.1. Az MI-kategorizálás alapértelmezetten **ki van kapcsolva**. Bekapcsolni csak a csoport adminisztrátora tudja, és csak akkor, ha a csoport minden tagja az Adatkezelési tájékoztató szerinti külön hozzájárulását megadta.

9.2. Bekapcsolt állapotban tételenként kizárólag a kereskedő neve, a leírás és az összeg kerül az Anthropic PBC (Egyesült Államok) szolgáltatásába. Tagazonosító, e-mail-cím, számlaszám, partnernév vagy más tétel nem.

9.3. Az MI javaslata hibás lehet. Ha bizonytalan, a FinSync „Bizonytalan" jelzést ad, és a tag döntését kéri. Egy tag által megadott kategóriát az MI soha nem írja felül.

9.4. Az MI-kategorizálás nem minősül a Felhasználóra joghatással járó automatizált döntéshozatalnak; csak a megjelenítést befolyásolja.

## 10. Tiltott felhasználás

A Felhasználó nem jogosult

a) a FinSyncet jogszabályba ütköző célra vagy más személy adatainak jogosulatlan gyűjtésére használni;
b) a szervert túlterhelni, feltörni, biztonsági mechanizmusait megkerülni, más csoport adataihoz hozzáférni próbálni (biztonsági hibát felfedezve azt jóhiszeműen az Üzemeltetőnek kell jelezni, nem kihasználni);
c) fiókját vagy hozzáférési kulcsát másnak átadni;
d) a FinSyncet harmadik személyeknek szolgáltatásként nyújtani;
e) hamis vagy más nevében készült adatot szándékosan rögzíteni.

## 11. Adatkezelés

11.1. A Felhasználó személyes adatainak kezelését az [Adatkezelési tájékoztató](adatkezelesi-tajekoztato-hu.md) írja le. A tájékoztató nem része ennek a szerződésnek, a Felhasználó azt a szerződéstől külön kapja meg.

11.2. Az MI-kategorizáláshoz adott hozzájárulás önkéntes, ennek a szerződésnek nem feltétele, és bármikor visszavonható.

## 12. Rendelkezésre állás, adatmentés

12.1. Az Üzemeltető a szolgáltatás folyamatos elérhetőségét nem vállalja, de törekszik arra, hogy a hibákat ésszerű időn belül elhárítsa.

12.2. Az Üzemeltető naponta titkosított biztonsági mentést készít [ELLENŐRIZENDŐ: a B1 pont elkészülte]. Ennek ellenére adatvesztés előfordulhat; a FinSync nem az egyetlen hely, ahol a Felhasználó pénzügyi adatai megvannak (lásd 4.2. pont).

## 13. Felelősség

13.1. A FinSync ingyenes tesztszoftver, amelyet az Üzemeltető „úgy, ahogy van" alapon, kifejezett vagy hallgatólagos szavatosság nélkül bocsát rendelkezésre, a jogszabály által megengedett legnagyobb mértékben.

13.2. Az Üzemeltető – a jogszabály által megengedett mértékben – nem felel
a) a hiányos, kettőzött, rosszul párosított vagy rosszul kategorizált tételekből;
b) a szolgáltatás elérhetetlenségéből;
c) a FinSync adatai alapján hozott pénzügyi döntésekből;
d) a Felhasználó telefonjának, bankalkalmazásának vagy az Android rendszernek a működéséből;
e) a Felhasználó jelszavának vagy kulcsának általa okozott kiszivárgásából
eredő károkért.

13.3. A felelősségkorlátozás **nem vonatkozik** a szándékosan vagy súlyos gondatlansággal okozott, valamint az emberi életet, testi épséget vagy egészséget megkárosító szerződésszegésre (Polgári Törvénykönyv, 2013. évi V. törvény, 6:152. §), és nem érinti a Felhasználó adatvédelmi jogszabályokból eredő jogait (GDPR 82. cikk).

## 14. A szerződés időtartama és megszűnése

14.1. A szerződés az elfogadással jön létre, és határozatlan ideig, legfeljebb a tesztüzem végéig tart.

14.2. A Felhasználó **bármikor, indoklás nélkül** felmondhatja: az Android-alkalmazást eltávolítja, és kéri az Üzemeltetőtől fiókja és adatai törlését vagy kiadását.

14.3. Az Üzemeltető 14 napos határidővel felmondhatja; a 10. pont súlyos megsértése vagy biztonsági veszély esetén azonnal felfüggesztheti a hozzáférést, erről a Felhasználót haladéktalanul értesíti.

14.4. Megszűnéskor az Üzemeltető a Felhasználó kérésére 30 napon belül géppel olvasható formában (CSV vagy JSON) kiadja a Felhasználó adatait, majd az Adatkezelési tájékoztatóban leírt határidőn belül törli azokat.

## 15. Módosítás

15.1. Az Üzemeltető a szerződést módosíthatja. A módosított változatot és a változások összefoglalóját a hatálybalépés előtt legalább 14 nappal megküldi a Felhasználónak.

15.2. A módosítás csak a Felhasználó elfogadásával lép hatályba. Ha a Felhasználó nem fogadja el, a 14.2. pont szerint felmondhat; a módosítás elfogadásáig a korábbi változat érvényes.

## 16. Irányadó jog, vitarendezés

16.1. A szerződésre a magyar jog, különösen a Polgári Törvénykönyv és a szerzői jogról szóló 1999. évi LXXVI. törvény az irányadó.

16.2. A felek a vitákat elsősorban egymás közötti egyeztetéssel rendezik. A Felhasználó, mint fogyasztó, jogszabály szerinti jogait (például békéltető testülethez vagy bírósághoz fordulás) ez a szerződés nem korlátozza.

16.3. Ha a szerződés valamely rendelkezése érvénytelen, az a többi rendelkezés érvényességét nem érinti.

## 17. Elfogadás

A Felhasználó aláírásával vagy e-mailes válaszával (a verziószám és a dátum megjelölésével) kijelenti, hogy a szerződést és az Adatkezelési tájékoztatót megkapta, elolvasta, megértette, és a szerződést elfogadja.

| | |
| --- | --- |
| Felhasználó neve | |
| Dátum | |
| Aláírás | |
| Elfogadott verzió | 0.1 |
