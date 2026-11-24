# Hungarian terms of the manuscript

One Hungarian term per concept, the same as the web app shows (`web/src/components/AppShell.tsx`, `web/src/lib/format.ts`), so the thesis, the screenshots and the demo agree. `check_manuscript.py` reads the table below: a word in the **Avoid** column found in the manuscript is reported with the term to use. Extend the table when a new concept enters the text; keep one row per concept.

| Concept (code / English docs) | Term | Avoid |
| --- | --- | --- |
| event (one purchase, possibly several records) | esemény | tranzakciócsoport |
| record, transaction (one row from one source) | rekord | bejegyzéssor |
| source (`android_notification`, `file_import`, `manual`) | forrás (Értesítés, Fájl, Kézi) | adatforrás-típus |
| transaction matching | tranzakció-egyeztetés | párosítás, összefésülés |
| duplicate (the same purchase from two records) | duplikátum | másolat |
| look-alike separate purchases | hasonló, de különálló vásárlások | álduplikátum |
| review (W5, a member decides an uncertain match) | ellenőrzés | jóváhagyás, review |
| confirm (`Ugyanaz a vásárlás`) | megerősítés | elfogadás |
| reject (`Két külön vásárlás`) | elutasítás | – |
| split (an event's record made separate again) | szétválasztás | leválasztás |
| decision history | döntési előzmények | naplózás |
| suggested category | kategória-javaslat | tipp |
| uncertain category (abstention) | bizonytalan kategória | ismeretlen kategória |
| mixed purchase | vegyes vásárlás | kevert kosár |
| category lines | kategóriasorok | altételek |
| transfer between own accounts | átvezetés | belső utalás |
| group (household) | csoport | háztartás-fiók |
| member | tag | felhasználó-tag |
| merchant rule (W8) | csoportszabály | kereskedőszabály |
| large language model | nagy nyelvi modell (LLM) | MI-modell |
| development / test split | fejlesztési / tesztrész | tanító halmaz |
| baseline | alapmódszer | baseline |
| coverage / accuracy | lefedettség / pontosság | – |
| agent skill (`.claude/skills/`) | ágensskill | készség |
| API token | API-token | API-kulcs |
