# Profile — Yan Lukashevich (facts)

Source of truth for every **factual** answer the Applier gives. Facts and reusable
answer-strings only — no behavior rules (those live in `applier_instructions.md`).
When this file and the playbook disagree on a fact, this file wins.

## Personal
- Full name: **Yan Lukashevich**  (first: Yan · last: Lukashevich)
- Email: **yanlukashevich2@gmail.com**
- Phone: **793233209**  (E.164: **+48793233209**)
- Location: Toruń, ul. Św. Józefa, 87-100, woj. kujawsko-pomorskie, Polska
- Willing to relocate: **yes**

## Links
- GitHub: https://github.com/yanlukashevich
- Portfolio: https://drukmruk.pl
- LinkedIn: https://www.linkedin.com/in/yan-lukashevich

## Work authorization
- Status: **permanent residence** (karta stałego pobytu) · needs sponsorship: **no** · EU work rights: **yes**
- PL answer: „Posiadam kartę stałego pobytu — pełne prawo do pracy w Polsce, bez konieczności sponsoringu.”
- EN answer: "I hold a permanent residence permit — full right to work in Poland, no visa/permit sponsorship required."

## Availability
- Notice period: **od zaraz** / *immediately available*
- Work mode: najlepiej zdalne, ale hybrydowe lub stacjonarne też OK / *remote preferred, hybrid or on-site also fine*

## Employment
- Contract types: **umowa o pracę preferred**, B2B also fine
- Expected salary: **10000 PLN / month, gross**
- Hourly rate (per-hour / B2B forms): **60 PLN / hour**

## Languages
- Polish — **C2**
- English — **C1**
- Russian — **C2**

**CEFR → descriptive-label mapping** (for forms like eRecruiter that use words, not A1–C2):
C2 → „Ojczysty" (or „Biegły"/„Native" if offered) · C1 → „Zaawansowany" · B2 →
„Średnio-zaawansowany" · B1 → „Średni" · A1–A2 → „Podstawowy". So: Polish → Ojczysty,
English → Zaawansowany, Russian → Ojczysty.

## Headline
Full-stack Developer — .NET · React · Azure · Python

## Story (osobisty wątek — surowiec na „opowiedz o sobie", „dlaczego IT", motywację)
Sięgaj tu, kiedy pytanie dotyczy **jego**, a nie technologii z oferty. Wybierz jeden wątek
pasujący do pytania — nigdy nie przepisuj całej listy.
- Zaczęło się od matematyki i fizyki w szkole — przygotowań do międzynarodowej olimpiady
  z fizyki i astronomii — i równolegle od IoT po godzinach: minirobotów i czujników.
- To połączenie fizyki z informatyką dało mu pierwszą pracę: UMK zlecił mu (dwuletnia umowa
  zlecenia) napisanie oprogramowania do obliczeń kwantowochemicznych dla grupy badawczej.
  Soft jest używany przez grupę, udostępniony społeczności naukowej do dalszego rozwoju,
  a o nim samym przygotowywany jest artykuł naukowy.
- Potem zespół i produkt: lider czteroosobowego zespołu przy symulatorze respiratora dla
  medyków (dwie nagrody finansowe, powstaje spółka spin-off UMK), a następnie własny
  komercyjny system druku DrukMruk — od zera do produkcji w 3 miesiące, w pojedynkę.
- Teraz siedzi w AI: buduje agentową platformę do szukania pracy (LLM + MCP), która sama
  analizuje oferty i wypełnia formularze w realnej przeglądarce — najciekawsze jest w niej
  zbieranie statystyk, analizowanie danych oraz precyzyjne i stabilne sterowanie agentami.
- Wspólny wątek: bierze realny problem konkretnych ludzi — naukowców, medyków, studentów —
  i dowozi go do końca, także wtedy, gdy bariera okazuje się biznesowa albo formalna,
  a nie techniczna.

## Pitch — kąty natarcia (wybierz JEDEN pod to, czego oferta naprawdę potrzebuje)
Nie ma jednego pitchu. Nazwij prawdziwą potrzebę z ogłoszenia — kto będzie tego używał, co
im się psuje, za co rozliczają ten etat — i uderz **jednym** kątem, tym, który do niej pasuje.
Każdy kąt to prawdziwe doświadczenie nazwane mocno.

Lista niżej to tylko częste przypadki. **Gdy oferta prosi o coś, czego tu nie ma — poszukaj
sam** w Experience, Projects i Story: prawie zawsze coś tam jest, tylko pod inną nazwą.

- **Frontend** — sygnały: React, TypeScript, UI, komponenty, RWD, dostępność, design system.
  → Cały front produkcyjnego systemu druku (React 19, TypeScript, Vite, Tailwind,
  i18n, a11y) — na nim realni użytkownicy zamawiają i płacą, więc UI musiał być zrozumiały
  dla przypadkowego studenta pod kioskiem. Wcześniej front panelu trenera w symulatorze
  (React), strona grupy badawczej i kokpit webowy platformy agentowej.
- **Backend w Pythonie** — sygnały: Python, FastAPI, Django/Flask, skrypty, integracje, ETL.
  → Python to jego najdłuższy język (3 lata): dwa lata pisania biblioteki obliczeniowej dla
  grupy badawczej UMK — modularna architektura, testy (pytest), wydajność liczona na
  klastrze — plus dwa własne serwisy FastAPI w produkcji (agent na kioskach, kokpit
  platformy agentowej) i automatyzacja w bashu.
- **Backend w JS / Node** — sygnały: Node.js, NestJS, Express, TypeScript po stronie serwera.
  → Backend symulatora respiratora: Node.js + NestJS, komunikacja w czasie rzeczywistym
  (WebSocket) i REST między panelem trenera a stanowiskami, SQLite, konteneryzacja —
  system działał stabilnie przy ~15 równoczesnych stanowiskach.
- **AI / LLM / agenty / ML** — sygnały: LLM, RAG, agent, prompt engineering, OpenAI/Claude,
  ML, „AI-first". → Jego działka i jego pasja; mów o tym wprost. Buduje produkcyjny system
  wieloagentowy (LLM + MCP), który sam prowadzi aplikacje w realnej przeglądarce: 10 000+
  przeanalizowanych ofert, ~95% formularzy end-to-end. Prompty wersjonowane i testowane jak
  kod (~2× mniej tokenów), a triage świadomie przeniesiony z modelu na deterministyczny kod
  tam, gdzie LLM się nie opłacał. Wcześniej trenowanie modeli (scikit-learn) i integracja
  LLM z aplikacjami.
- **Dane / analityka / BI / raportowanie / R&D** — sygnały: SQL, pandas, raporty, dashboard,
  KPI, hurtownia, „data-driven", badania. → Dwa lata analizy danych naukowych na UMK:
  zbierał, przygotowywał i analizował dane, budował statystyki i interpretował wyniki, co
  pozwoliło osadzić to oprogramowanie w doświadczeniach i referencjach naukowych
  i potwierdzić poprawność jego działania; do tego raporty i wizualizacje dla odbiorców
  nietechnicznych (NumPy, pandas, matplotlib, SQL). W platformie agentowej robi to samo dla
  siebie: statystyki z logów, scoring ofert i koszt tokenów policzone z danych, nie z
  przeczucia.
- **Cloud / DevOps / SRE / bezpieczeństwo** — sygnały: Azure/AWS, Kubernetes, Terraform,
  CI/CD, on-call, ISO/RODO, security. → Sam utrzymuje całą produkcyjną chmurę bez osobnego
  DevOps: Azure (App Service, SQL, Key Vault, VNet, Managed Identity, Application Insights),
  CI/CD w GitHub Actions z federacją OIDC, Docker. Przeszedł miesięczny audyt bezpieczeństwa
  instytucji publicznej — obrona architektury i hardening przed uczelnianym zespołem
  bezpieczeństwa, ocena pozytywna warunkowała wdrożenie.
- **Embedded / IoT / hardware** — sygnały: Raspberry Pi, urządzenie, czujniki, firmware,
  kiosk, terminal, produkcja. → Trzy różne projekty z prawdziwym sprzętem: autonomiczne
  kioski druku (Raspberry Pi 5, single-purpose terminal, własne LTE, utwardzone pod realny
  model zagrożeń miejsca publicznego), stanowiska symulatora respiratora (ekran dotykowy,
  pokrętła, obudowa) i jeszcze szkolne miniroboty — od nich się zaczęło.
- **Backend / fullstack / .NET / web (domyślny)** — gdy oferta jest po prostu ogólna.
  → Od zera do produkcji w 3 miesiące, w pojedynkę: komercyjny system druku samoobsługowego
  (ASP.NET Core 8, React 19 / TypeScript, Azure) — od koncepcji i kodu przez płatności
  (odporna na awarie integracja Autopay, webhooki, zwroty), chmurę i CI/CD po klienta
  instytucjonalnego. Doprowadza projekty do końca niezależnie od tego, czy bariera jest
  techniczna, biznesowa czy formalna.

## Tech stack
- **Backend:** C#, ASP.NET Core 8, Entity Framework Core, REST API, WebSocket · Node.js, NestJS · Python (FastAPI)
- **Frontend:** React 19, TypeScript, JavaScript, Vite, Tailwind CSS, i18n, accessibility (a11y)
- **Cloud / DevOps:** Microsoft Azure (App Service, SQL Database, Service Bus, Blob Storage, Key Vault, Virtual Network, Managed Identity, Application Insights), Azure CLI, GitHub Actions (CI/CD, OIDC), Docker, Docker Compose
- **Linux / networking:** bash automation, HPC cluster, PBS, conda, network admin (AP, DHCP, DNS, NAT, SSH), Cisco CCNA
- **Databases:** Azure SQL, SQLite (EF Core), MongoDB
- **Security:** defense-in-depth, threat modeling, Managed Identity + Key Vault, GDPR (privacy by design)
- **Python / AI / data:** NumPy, SciPy, pandas, matplotlib, Jupyter, scikit-learn, LLM integration into applications · Psi4 · systemy agentowe (orkiestrator + subagenty), MCP, prompt engineering
- **Testing / processes:** TDD, xUnit, pytest, Jest, integration testing, Git / GitHub flow, code review, Scrum
- **Embedded / IoT:** Raspberry Pi (Pi 4/5, Pico), MicroPython, GPIO, sensors (IMU, encoders), I2C, serial

## Years per technology
(Years, consistent with the CV.)

| Tech | Years | Tech | Years |
|------|-------|------|-------|
| Python | 3 | Azure | 2 |
| C# / .NET | 2 | Docker | 2 |
| ASP.NET Core | 2 | Linux | 4 |
| React | 2 | SQL | 3 |
| TypeScript | 2 | Git | 4 |
| JavaScript | 3 | Node.js / NestJS | 1 |

## Experience
Pisane tak, jak on sam o tym opowiada — bierz stąd **jeden konkret** pasujący do oferty
(domena, technologia, rola), nie streszczenie całej pozycji.

### DrukMruk — Founder & Lead Developer · 02.2026 – obecnie · własna działalność · drukmruk.pl
- Od zera do produkcji w 3 miesiące, w pojedynkę — komercyjny, rozproszony system samoobsługowego druku dla społeczności akademickiej: frontend webowy (React 19 / TypeScript) + backend chmurowy (ASP.NET Core 8, Azure) + sieć fizycznych kiosków IoT (Raspberry Pi 5).
- Przeszedł miesięczny audyt bezpieczeństwa instytucji publicznej (UCI UMK) — w kilku rundach z uczelnianym zespołem bezpieczeństwa obronił architekturę i utwardził system (izolacja sieciowa warstw, ograniczenie ekspozycji publicznej, wzmocniona ochrona danych, centralne logowanie i alertowanie incydentów); pozytywna ocena warunkowała wdrożenie w infrastrukturze uczelni.
- Zbudował i utrzymuje cały backend chmurowy — ASP.NET Core 8 na Azure, CI/CD w GitHub Actions (federacja OIDC), projektowany „security-first". W nim odporna na awarie integracja płatności (Autopay): inicjacja transakcji, kryptograficznie weryfikowane webhooki, automatyczne zwroty, gwarancja spójności stanu między płatnością a wydrukiem; krytyczne przepływy pokryte testami (TDD).
- Zaprojektował autonomiczne stacje druku gotowe do pracy bez nadzoru w przestrzeni publicznej — Raspberry Pi 5 z ekranem dotykowym i drukarką w zamkniętej obudowie, jako single-purpose terminal (lokalny agent FastAPI), każda na własnym LTE, w pełni odizolowana od sieci uczelni. Utwardzenie warstwowe (defense-in-depth) pod realny model zagrożeń miejsca publicznego: dostęp fizyczny, próby wyjścia z trybu kiosku, brute-force kodów odbioru, kradzież danych, infekcja systemu.
- Wygrał Copernicus Startup Stars 2026 — pierwsze miejsce w konkursie startupowym z projektem DrukMruk.
- Przeprowadził projekt przez całą ścieżkę formalno-biznesową — badanie potrzeb, iteracje dokumentacji technicznej, oficjalne wnioski, negocjacje z władzami UMK (kanclerz, dyrekcja Biblioteki Głównej, dyrektorzy instytutów, władze dziekańskie, fundacja uczelni); mimo początkowych odmów uzyskał oficjalne pozwolenie na rozmieszczenie kiosków. Założył działalność, napisał politykę prywatności i regulaminy, prowadzi księgowość.

### Uniwersytet Mikołaja Kopernika w Toruniu (UMK) — programista naukowy (chemia kwantowa) · umowa zlecenia · 02.2024 – 03.2026
- Dwuletnie zlecenie z UMK dzięki połączeniu fizyki z informatyką: stworzenie oprogramowania do obliczeń kwantowochemicznych używanego przez grupę badawczą i udostępnionego społeczności naukowej do dalszego rozwoju; przygotowywany jest o nim artykuł naukowy.
- Zaprojektował i napisał modułową bibliotekę obliczeniową w Pythonie — implementacja zaawansowanych algorytmów matematycznych i fizyki kwantowej, dająca innym naukowcom narzędzie do liczenia autorską metodą grupy; szybsza od metod tej samej klasy dokładności i łatwa do rozszerzania.
- Zbierał, przygotowywał i analizował dane naukowe, budował statystyki i interpretował wyniki — dzięki temu udało się osadzić to oprogramowanie w doświadczeniach i referencjach naukowych, potwierdzić poprawność jego działania i zebrać dowody do publikacji (NumPy, pandas, matplotlib).
- Zrobił warstwę kontaktu człowieka z softem — interfejs użytkownika, generowanie raportów, wizualizację i eksport wyników, dzięki czemu korzystają z niego ludzie stricte od fizyki, nie programiści.
- Pracował na wysokowydajnym klastrze — własne skrypty do kolejkowania i uruchamiania zadań oraz do analizy obciążenia i zbierania statystyk; na tej podstawie stopniowo przyspieszał obliczenia (seria z ~doby do godziny) i naprawiał błędy (Linux, bash, conda, PBS).
- Wdrożył oprogramowanie w grupie badawczej — przygotowywał środowiska na klastrze dla członków grupy, reagował na zgłoszenia, pisał dokumentację. Zbudował i administruje stroną grupy: szsmiga.fizyka.umk.pl.

## Projects
### Symulator respiratora (Respirator-simulator) — lider zespołu · 2026 · zamówienie Centrum Symulacji Medycznych UMK
https://github.com/yanlukashevich/Respirator-simulator
- Rok pracy jako lider czteroosobowego zespołu: kompleksowy system do treningu respiracji dla personelu medycznego — połączone w sieć fizyczne symulatory (Raspberry Pi, ekran dotykowy, pokrętła, obudowa), panel administratora zajęć (przypisywanie zajęć, analiza przebiegu, wizualizacja wyników i trendów) oraz silnik symulacyjny zbudowany na podstawie publikacji naukowych, pozwalający numerycznie odtworzyć szeroki zakres sytuacji klinicznych.
- Prezentował i obronił rozwiązanie na konkursach UMK i przed spółką startową — dwie nagrody finansowe (1. miejsce w konkursie Instytutu Fizyki, laureat konkursu ogólnouczelnianego); powstaje spółka spin-off UMK do dalszego rozwoju projektu.
- Jego rola: badania i zbieranie wymagań medycznych, organizacja zespołu, prowadzenie backlogu i pilnowanie zgodności ze Scrumem — dzięki temu tempo pracy było stabilne przez cały cykl developmentu.
- Zaprojektował, skonfigurował i przetestował sieć projektu od zera (AP, DHCP, DNS, NAT, SSH) — skalowanie z 2 do ~15 stabilnie działających stanowisk.
- Pracował też przy froncie (React, TypeScript, Vite, Tailwind), backendzie (Node.js, NestJS), komunikacji między urządzeniami (WebSocket, REST), bazie (SQLite) i konteneryzacji. Obecnie buduje nowy silnik symulacyjny, obejmujący szerszy zakres programu szkoleniowego.

### Claude Job Searcher — agentowa platforma do szukania pracy · 2026
https://github.com/yanlukashevich/claude-job-searcher
- System, który przekopuje tysiące ogłoszeń, wyławia realnie pasujące i sam prowadzi aplikacje, a człowiek zatwierdza każdą kluczową decyzję — 10 000+ zebranych i przeanalizowanych ofert, ~95% formularzy wypełnianych end-to-end bez poprawek człowieka.
- Architektura wieloagentowa z realnym podziałem odpowiedzialności — pythonowy finder pobiera oferty z publicznych API do append-only bazy i deterministycznie je punktuje, kokpit webowy (FastAPI) łączy je z historią aplikacji, a orkiestrator uruchamia po jednym świeżym subagencie na ofertę: rozpoznaje formularz (modal portalu albo zewnętrzny ATS — Greenhouse, Lever, Workable, SmartRecruiters), mapuje pola, komponuje odpowiedzi otwarte, załącza właściwy wariant CV i loguje wynik. Jedno wąskie zadanie na komponent pozwoliło zejść na tańszy model, a świeży kontekst izoluje błędy.
- Kod tam, gdzie kod wygrywa; LLM tylko tam, gdzie potrzebne jest rozumowanie — triage oparty na modelu językowym palił za dużo tokenów, więc zastąpił go deterministycznym scoringiem (tytuły, tagi umiejętności, opisy, sygnały firmowe): zero tokenów, powtarzalnie i audytowalnie.
- Prompty traktuje jak kod — wersjonowane, testowane i optymalizowane w osobnej pętli trenującej na ofertach testowych: ~2× mniejsze zużycie tokenów na aplikację, dostrojone do realnych trybów awarii z logów. Tak samo decyzje techniczne: metody wprowadzania danych do przeglądarki zmierzył na poziomie zdarzeń DOM, zanim wybrał strategię interakcji.
- Bezpieczeństwo z konstrukcji, nie z reguł w prompcie — agent jest zamontowany na dokładnie jednym folderze i fizycznie nie widzi niczego powyżej, więc baza ofert i kod findera są dla niego nieosiągalne, a nie „zakazane"; to skróciło prompty i uczyniło całą klasę błędów niemożliwą z definicji.
- Człowiek w pętli, a twardych faktów system nigdy nie zmyśla — domyślny tryb review zatrzymuje agenta przed wysłaniem, dane faktograficzne pochodzą wyłącznie z pliku faktów, wymagane pole bez znanej odpowiedzi to blokada do ręcznej obsługi, a każda odpowiedź jest logowana dosłownie.

## Education
- Informatyka Stosowana, studia inżynierskie (inż.) — Uniwersytet Mikołaja Kopernika w Toruniu, 2022 – 2026

## Certificates
- Cisco CCNA

## Why-me material (jednolinijkowe haki — szczegóły w Experience / Projects)
- Dowożę od zera do produkcji — komercyjny system .NET 8 / React / Azure wdrożony w 3 miesiące dla klienta instytucjonalnego.
- Full-stack end-to-end: front (React/TS), backend (ASP.NET Core / FastAPI), chmura (Azure), CI/CD, płatności, bezpieczeństwo.
- Zdany audyt bezpieczeństwa instytucji publicznej — realny threat modeling i hardening, nie teoria.
- Dwa lata Pythonu naukowego na UMK — biblioteka obliczeniowa dla całej grupy badawczej i automatyzacja klastra HPC.
- Prowadzę zespoły i projekty do wyniku — 1. miejsce w konkursie, laureat, wejście w komercjalizację (spin-off).
- Praktyczne AI — produkcyjny system wieloagentowy (LLM + MCP) z izolacją kontekstu i audytowalnym logiem decyzji.
- Doprowadzam rzeczy do końca niezależnie od bariery: technicznej, biznesowej czy formalnej.

## What I'm looking for / motivation (canonical answers)
For questions like „czego szukasz?", „dlaczego zmieniasz pracę?", „motywacja do zmiany":

- **Czego szukam — PL:** „Zależy mi na pracy w zespole, w którym mogę się uczyć od lepszych
  i robić ambitne rzeczy. Doceniam dobrą atmosferę, dzielenie się wiedzą, szkolenia
  i elastyczność (praca zdalna/hybrydowa)."
- **What I'm looking for — EN:** "I want to work in a team where I can learn from people
  better than me and build ambitious things. I value a good atmosphere, knowledge sharing,
  training, and flexibility (remote/hybrid work)."
- **Motywacja do zmiany — PL:** „Teraz chcę rozwijać się w większym, doświadczonym zespole,
  żeby w przyszłości móc wejść w rolę lidera."
- **Motivation to change — EN:** "I now want to grow in a larger, experienced team so that
  in the future I can step into a leadership role."
- **Kilka słów o sobie — PL:** „Zaczynałem od fizyki i matematyki — startów w olimpiadzie
  i lutowania minirobotów po godzinach — i to zaprowadziło mnie do programowania. Przez dwa
  lata pisałem na UMK oprogramowanie do obliczeń kwantowych dla grupy badawczej, potem
  prowadziłem czteroosobowy zespół przy symulatorze respiratora dla medyków, a ostatnio
  sam zbudowałem i wdrożyłem komercyjny system druku na uczelni. Teraz najwięcej czasu
  zajmuje mi AI — buduję system agentowy (LLM + MCP), który sam analizuje oferty pracy
  i wypełnia formularze w przeglądarce. Najbardziej lubię brać realny problem konkretnych
  ludzi i doprowadzać go do działającego produktu."
- **A few words about me — EN:** "I started with physics and maths — competing in olympiads
  and soldering little robots after school — and that led me into programming. I spent two
  years at NCU writing quantum-chemistry software for a research group, then led a team of
  four building a ventilator simulator for medical training, and most recently designed and
  shipped a commercial self-service printing system on my own. Right now most of my time
  goes into AI — I'm building an agentic system (LLM + MCP) that analyses job offers and
  fills in application forms in a real browser. What I enjoy most is taking a real problem
  real people have and turning it into something that actually works."

## CV variants
Files under `CV_PDF/`. Default variant = **universal**.

| Offer stack | PL file | EN file |
|-------------|---------|---------|
| python | `CV_PDF/CV_Yan_Lukashevich_python/CV_Yan_Lukashevich.pdf` | `CV_PDF/CV_Yan_Lukashevich_python/CV_Yan_Lukashevich_EN.pdf` |
| dotnet | `CV_PDF/CV_Yan_Lukashevich_dotnet_fullstack/CV_Yan_Lukashevich.pdf` | `CV_PDF/CV_Yan_Lukashevich_dotnet_fullstack/CV_Yan_Lukashevich_EN.pdf` |
| cloud / devops | `CV_PDF/CV_Yan_Lukashevich_cloud_devops/CV_Yan_Lukashevich.pdf` | `CV_PDF/CV_Yan_Lukashevich_cloud_devops/CV_Yan_Lukashevich_EN.pdf` |
| universal (default) | `CV_PDF/CV_Yan_Lukashevich_universal/CV_Yan_Lukashevich.pdf` | `CV_PDF/CV_Yan_Lukashevich_universal/CV_Yan_Lukashevich_EN.pdf` |
