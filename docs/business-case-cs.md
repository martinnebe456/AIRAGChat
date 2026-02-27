# AIRAGChat – ukázka řešení pro vedení (interní AI chat nad firemní dokumentací)

## 1) Co je AIRAGChat a proč to má vedení zajímat

AIRAGChat je interně kontrolovaný nástroj, který umožňuje zaměstnancům chatovat nad firemními dokumenty a získávat odpovědi s citacemi zdrojů. Prakticky to znamená, že dokumentace přestane být jen „uložená“, ale začne být skutečně použitelná v každodenní práci.

### Co to řeší pro firmu (high-level)

- rychlejší hledání odpovědí v interních materiálech
- lepší využití metodik, směrnic a týmové dokumentace
- menší zátěž seniorních kolegů opakovanými dotazy
- řízené používání AI nad interními dokumenty (ne „volný chat bez kontroly“)
- jednoduché škálování na další týmy přes projektový model

**AIRAGChat je vhodný jak pro interní týmové KB, tak pro celofiremní chat nad metodikami – při zachování řízení přístupů a governance v našem nástroji.**

[BLOK OBRÁZKU – Hlavní obrazovka chatu (hero ukázka)]
- Co má být na ukázce: Hlavní chat UI s vybraným projektem, historií chatu a odpovědí s citacemi.
- Co má ukázka demonstrovat pro vedení: Že jde o praktický a použitelný interní nástroj, ne jen technický prototyp.
- Poznámka k citlivým údajům (co anonymizovat): Názvy projektů, jména uživatelů, interní otázky/odpovědi, názvy dokumentů.
[/BLOK OBRÁZKU]

## 2) Proč to řešit právě teď (business pain)

Ve firmách obvykle není hlavní problém to, že by dokumentace neexistovala. Problém je spíš v tom, že se s ní špatně pracuje.

- informace jsou v mnoha dokumentech a verzích
- zaměstnanci hledají správné odpovědi příliš dlouho
- znalosti zůstávají v hlavách klíčových lidí
- metodiky a směrnice se v praxi používají hůře, než by měly
- onboarding zatěžuje zkušenější kolegy opakovanými dotazy
- interní support týmy řeší opakovaně stejné dotazy

**Nejde o nedostatek dokumentace, ale o dostupnost a použitelnost znalostí v běžné práci.**

[BLOK OBRÁZKU – Dotaz a odpověď s citací]
- Co má být na ukázce: Reálný dotaz uživatele a odpověď s viditelnou citací/sources.
- Co má ukázka demonstrovat pro vedení: Převod dokumentace na rychle použitelnou odpověď s dohledatelností zdroje.
- Poznámka k citlivým údajům (co anonymizovat): Text dotazu, odpověď, názvy dokumentů, interní pasáže.
[/BLOK OBRÁZKU]

## 3) Jak to funguje v praxi (demo flow)

Uživatelský scénář je jednoduchý a intuitivní:

1. Uživatel si vybere projekt (např. týmová KB nebo centrální metodiky).
2. Položí otázku v chatu.
3. AIRAGChat hledá odpověď pouze v dokumentech daného projektu.
4. Vrátí odpověď s citacemi (zdroji).
5. Pokud chybí dokumentace nebo je neaktuální, tým ji doplní do projektu.
6. Dokument se zpracuje a je dostupný pro další dotazy.

Tím vzniká praktický cyklus: **dotaz -> odpověď -> doplnění znalostí -> lepší odpovědi příště**.

[BLOK OBRÁZKU – Výběr projektu v chatu]
- Co má být na ukázce: Přepnutí/výběr aktivního projektu při novém chatu.
- Co má ukázka demonstrovat pro vedení: Jednoduché použití a oddělení znalostí podle projektů.
- Poznámka k citlivým údajům (co anonymizovat): Názvy projektů a historie chatů.
[/BLOK OBRÁZKU]

[BLOK OBRÁZKU – Citace / Sources panel (sbalené a rozbalené)]
- Co má být na ukázce: Odpověď s tlačítkem Sources (N) a rozbalenými citacemi.
- Co má ukázka demonstrovat pro vedení: Dohledatelnost a vyšší důvěryhodnost odpovědí.
- Poznámka k citlivým údajům (co anonymizovat): Názvy dokumentů, snippet textů, interní obsah.
[/BLOK OBRÁZKU]

## 4) Kde to může firma použít hned (management use case gallery)

### 4.1 Interní týmová KB (self-service)

- **Kde to pomůže:** Týmové know-how, interní postupy, opakované otázky v týmu.
- **Co se typicky nahrává:** FAQ, postupy, checklisty, týmové standardy, manuály.
- **Business přínos:** Tým získá vlastní použitelnou KB bez trvalé závislosti na IT.
- **Jak se řídí přístupy:** IT založí projekt a role; tým si v rámci projektu spravuje obsah.

[BLOK OBRÁZKU – Document Library projektu (týmová KB)]
- Co má být na ukázce: Dokumentová knihovna konkrétního projektu s přehledem dokumentů.
- Co má ukázka demonstrovat pro vedení: Self-service práce týmu s vlastní znalostní bází.
- Poznámka k citlivým údajům (co anonymizovat): Názvy dokumentů, projekty, uživatelé.
[/BLOK OBRÁZKU]

### 4.2 Celofiremní metodiky a směrnice

- **Kde to pomůže:** Metodiky, interní pravidla, procesní dokumentace.
- **Co se typicky nahrává:** Směrnice, procesy, interní policy dokumenty, standardy.
- **Business přínos:** Vyšší využití metodik v praxi a rychlejší orientace zaměstnanců.
- **Jak se řídí přístupy:** Centrální projekt s řízeným read-only nebo role-based přístupem.

### 4.3 Onboarding nových zaměstnanců

- **Kde to pomůže:** Základní orientace, interní pravidla, procesy, FAQ.
- **Co se typicky nahrává:** Onboarding manuály, interní standardy, organizační přehledy.
- **Business přínos:** Rychlejší adaptace a menší zátěž mentorů/seniorů.
- **Jak se řídí přístupy:** Onboarding projekt podle role/týmu.

### 4.4 IT / interní podpora / servisní KB

- **Kde to pomůže:** Opakované interní požadavky, troubleshooting, provozní postupy.
- **Co se typicky nahrává:** Runbooky, SOP, návody, interní support FAQ.
- **Business přínos:** Potenciál zrychlit řešení opakovaných požadavků a zvýšit konzistenci odpovědí.
- **Jak se řídí přístupy:** Samostatné projekty dle citlivosti a typu supportu.

[BLOK OBRÁZKU – Fronta a stav zpracování dokumentů]
- Co má být na ukázce: Queue/processing monitor s přehledem queued / running / done / failed.
- Co má ukázka demonstrovat pro vedení: Že zpracování dokumentů je transparentní a kontrolovatelné.
- Poznámka k citlivým údajům (co anonymizovat): Názvy dokumentů, projekty, interní log texty.
[/BLOK OBRÁZKU]

### 4.5 Projektová izolace znalostí (oddělení týmů)

- **Kde to pomůže:** Projekty/oddělení s odděleným know-how nebo citlivější dokumentací.
- **Co se typicky nahrává:** Projektové specifikace, interní rozhodnutí, návody, procesní dokumenty.
- **Business přínos:** Odpovědi jsou relevantnější a nedochází k míchání znalostí mezi týmy.
- **Jak se řídí přístupy:** Každý projekt má vlastní členy a role.

[BLOK OBRÁZKU – Chat v konkrétním projektu (izolace)]
- Co má být na ukázce: Chat s viditelným aktivním projektem a odpovědí z dokumentů tohoto projektu.
- Co má ukázka demonstrovat pro vedení: Izolaci znalostí a bezpečnější práci napříč týmy.
- Poznámka k citlivým údajům (co anonymizovat): Názvy projektů, otázky, odpovědi, názvy dokumentů.
[/BLOK OBRÁZKU]

### 4.6 Management / compliance / auditní dohled

- **Kde to pomůže:** Metodiky, compliance, auditní příprava, interní standardy.
- **Co se typicky nahrává:** Politiky, kontrolní checklisty, metodiky a standardy.
- **Business přínos:** Lepší kontrola nad tím, kdo pracuje s jakými znalostmi a jak se používají interní materiály.
- **Jak se řídí přístupy:** Role a projektová governance s centrálním dohledem.

[BLOK OBRÁZKU – Správa projektů a členů]
- Co má být na ukázce: Správa projektů, členů a rolí (viewer/contributor/manager).
- Co má ukázka demonstrovat pro vedení: Governance model a řízené přístupy v praxi.
- Poznámka k citlivým údajům (co anonymizovat): Jména, e-maily, názvy týmů/projektů.
[/BLOK OBRÁZKU]

## 5) Proč je to pro firmu bezpečné a kontrolovatelné

AIRAGChat není „volný AI chat“. Je to řízené prostředí pro práci s interními znalostmi.

### Co je pod kontrolou

- přístupy podle projektů a rolí
- oddělení znalostí mezi projekty
- centrální nastavení a správa nástroje
- stav zpracování dokumentů (fronta, průběh, dokončení/chyba)
- transparentnost provozu a dohledatelnost práce s dokumenty
- správa citlivých klíčů centrálně (ne v prohlížeči uživatelů)

**Klíčová výhoda pro vedení: týmy mohou nástroj používat samostatně, ale stále v rámci jasně řízeného governance modelu.**

[BLOK OBRÁZKU – Centrální administrace a nastavení]
- Co má být na ukázce: System Settings / model settings / stav klíčů a centrálních nastavení (bez citlivých dat).
- Co má ukázka demonstrovat pro vedení: Centrální řízení a bezpečnostní kontrolu.
- Poznámka k citlivým údajům (co anonymizovat): Klíče, interní názvy konfigurací, provozní detaily.
[/BLOK OBRÁZKU]

[BLOK OBRÁZKU – Processing logs / dohled nad dokumentem]
- Co má být na ukázce: Detail průběhu zpracování dokumentu (stav, kroky, logy).
- Co má ukázka demonstrovat pro vedení: Transparentnost a kontrola při zpracování dokumentace.
- Poznámka k citlivým údajům (co anonymizovat): Názvy dokumentů, logy se specifickými interními informacemi.
[/BLOK OBRÁZKU]

## 6) Jak se to škáluje ve firmě (prodejní argument pro vedení)

**Škálování je velmi jednoduché: IT založí nový projekt, nastaví oprávnění a nové oddělení může prakticky ze dne na den začít intuitivně používat vlastní KB ve stejném nástroji.**

### Jak vypadá škálování v praxi

- IT / admin založí projekt a nastaví role
- `manager` v projektu spravuje uživatele a běžný provoz přístupů
- `contributor` nahrává a spravuje dokumenty
- `viewer` čte a chatuje nad dokumenty
- stejný governance model se opakuje napříč odděleními

**Role `manager` je klíčová pro self-service: tým přebírá odpovědnost za uživatele a dokumenty v rámci svého projektu, zatímco IT drží centrální rámec a kontrolu.**

[BLOK OBRÁZKU – Role v projektu (viewer / contributor / manager)]
- Co má být na ukázce: Obrazovka správy členů projektu s rolemi a oprávněními.
- Co má ukázka demonstrovat pro vedení: Praktickou delegaci odpovědnosti na tým bez ztráty governance.
- Poznámka k citlivým údajům (co anonymizovat): Jména, e-maily, názvy projektů.
[/BLOK OBRÁZKU]

[BLOK OBRÁZKU – Self-service workflow týmu]
- Co má být na ukázce: Projektová knihovna dokumentů + akce upload/reprocess v rámci projektu spravovaného týmem.
- Co má ukázka demonstrovat pro vedení: Jak tým funguje samostatně v rámci řízeného modelu.
- Poznámka k citlivým údajům (co anonymizovat): Názvy dokumentů, interní obsah, názvy projektů.
[/BLOK OBRÁZKU]

## 7) Orientační náklady a ekonomika pilotu (praktický signál pro rozhodnutí)

Pro vedení je důležité mít alespoň orientační představu o řádu nákladů.

### Orientační benchmark z dev testu

- zpracování několika e-knih (tj. několik tisíc stran plného textu)
- zpracování přes OpenAI vyšlo přibližně na **0,049 €**

### Jak tento údaj číst

- je to **ilustrativní benchmark**, ne garantovaná cena
- skutečné náklady se budou lišit podle objemu dat, typu dokumentů a zvoleného modelu
- pro pilot doporučujeme náklady průběžně sledovat a vyhodnocovat po use case kategoriích

**Pro management rozhodnutí je důležitý řád nákladů a možnost průběžné kontroly, ne jednorázové přesné číslo mimo reálný provoz.**

[BLOK OBRÁZKU – OpenAI dashboard (usage / náklady) pro dev test]
- Co má být na ukázce: Screenshot z OpenAI dashboardu s usage/cost za testovací období (uživatel může dodat vlastní ukázku).
- Co má ukázka demonstrovat pro vedení: Reálný příklad řádu nákladů a možnost průběžného sledování spotřeby.
- Poznámka k citlivým údajům (co anonymizovat): Organization ID, project názvy v OpenAI, API key metadata, další interní usage položky.
[/BLOK OBRÁZKU]

## 8) Doporučený pilot a rollout (akční plán)

### Fáze 1 – Pilot (1–2 týmy)

- **Cíl:** Ověřit užitečnost, adopci a governance model na konkrétních use case.
- **Kdo je zapojen:** IT + 1–2 vybrané týmy + business owner pilotu.
- **Co se vyhodnocuje:** využití, kvalita vstupních dokumentů, spokojenost uživatelů.

### Fáze 2 – Rozšíření na více oddělení

- **Cíl:** Ověřit opakovatelnost projektového modelu a rolí.
- **Kdo je zapojen:** IT + další vedoucí týmů / project manageři.
- **Co se vyhodnocuje:** škálovatelnost governance, jednoduchost správy přístupů.

### Fáze 3 – Centrální metodiky

- **Cíl:** Zavést celofiremní znalostní oblast (metodiky / směrnice).
- **Kdo je zapojen:** Vlastník metodik / compliance + IT.
- **Co se vyhodnocuje:** adopce napříč firmou, konzistence odpovědí, využití dokumentace.

### Fáze 4 – Standardizace governance

- **Cíl:** Formalizovat pravidla pro zakládání projektů, role a ownership obsahu.
- **Kdo je zapojen:** IT management + business owners.
- **Co se vyhodnocuje:** dlouhodobá udržitelnost a transparentní odpovědnosti.

[BLOK OBRÁZKU – Rollout roadmap (pilot → rozšíření)]
- Co má být na ukázce: Jednoduchá roadmapa/slide se 4 fázemi zavedení.
- Co má ukázka demonstrovat pro vedení: Že zavedení je řízené, postupné a měřitelné.
- Poznámka k citlivým údajům (co anonymizovat): Interní názvy oddělení, termíny, odpovědné osoby.
[/BLOK OBRÁZKU]

## 9) Co by mělo vedení schválit (rozhodovací část)

Pro smysluplný start doporučujeme schválit:

- pilotní use case (např. týmová KB + centrální metodiky)
- business ownera pilotu a partnera z IT
- governance rámec pro projekty a role
- pilotní KPI (adopce, využití, spokojenost, základní provozní metriky)
- termín vyhodnocení pilotu a rozhodnutí o rozšíření

**Doporučení: začít pilotem a rozhodovat o rozšíření na základě reálných výsledků, ne odhadů.**

[BLOK OBRÁZKU – Management KPI přehled (adopce a využití)]
- Co má být na ukázce: Přehled metrik pilotu/rozšíření (aktivní projekty, uživatelé, dokumenty, využití chatu).
- Co má ukázka demonstrovat pro vedení: Jak lze průběžně vyhodnocovat přínos nástroje.
- Poznámka k citlivým údajům (co anonymizovat): Názvy týmů/projektů, interní identifikátory.
[/BLOK OBRÁZKU]

## 10) Příloha – stručný slovníček pojmů

### KB (Knowledge Base / znalostní báze)
Sada dokumentů a znalostí, nad kterou lze vyhledávat a chatovat.

### Projekt
Oddělená znalostní oblast v nástroji s vlastními dokumenty, členy a rolemi.

### Role (viewer / contributor / manager / admin)
- **Viewer:** čte a chatuje nad dokumenty
- **Contributor:** nahrává a spravuje dokumenty v projektu
- **Manager:** spravuje členy projektu a běžný provoz přístupů
- **Admin:** centrálně spravuje systém a governance

### Chat nad dokumenty
Uživatel klade otázky a získává odpovědi z dokumentů dostupných v daném projektu.

### Citace zdroje
Odkaz na dokument/pasáž, ze které odpověď vychází.

## Doplňkové screenshot bloky (volitelné pro rozšířenou prezentaci)

[BLOK OBRÁZKU – Další ukázka dokumentového workflow (upload → fronta → hotovo)]
- Co má být na ukázce: Série nebo jedna obrazovka ukazující upload, zařazení do fronty a dokončené zpracování.
- Co má ukázka demonstrovat pro vedení: Že práce s dokumenty je řízená a provozně zvládnutelná.
- Poznámka k citlivým údajům (co anonymizovat): Názvy dokumentů, projekty, interní obsah.
[/BLOK OBRÁZKU]

[BLOK OBRÁZKU – Kvalitativní vyhodnocení / srovnání (volitelné)]
- Co má být na ukázce: Přehled kvalitativního vyhodnocení nebo srovnání (pokud bude vedení zajímat i řízení kvality).
- Co má ukázka demonstrovat pro vedení: Že řešení lze nejen používat, ale i průběžně vyhodnocovat.
- Poznámka k citlivým údajům (co anonymizovat): Dotazy, názvy datasetů, interní výsledky.
[/BLOK OBRÁZKU]
