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
- LinkedIn: *(brak / do uzupełnienia)*

## Work authorization
- Status: **permanent residence** (karta stałego pobytu) · needs sponsorship: **no** · EU work rights: **yes**
- PL answer: „Posiadam kartę stałego pobytu — pełne prawo do pracy w Polsce, bez konieczności sponsoringu.”
- EN answer: "I hold a permanent residence permit — full right to work in Poland, no visa/permit sponsorship required."

## Availability
- Notice period: **od zaraz** / *immediately available*
- Work mode: najlepiej zdalne, ale hybrydowe lub stacjonarne też OK / *remote preferred, hybrid or on-site also fine*

## Employment
- Contract types: **umowa o pracę** or **B2B** (no preference)
- Expected salary: **10000 PLN / month, gross** — negotiable (a starting point)

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

## Pitch (raw material for free-text answers)
**PL:** Samodzielnie zaprojektowałem, zbudowałem i wdrożyłem produkcyjnie komercyjny
system druku samoobsługowego (.NET 8, React 19 / TypeScript, Azure) — od koncepcji i kodu
przez płatności, chmurę i CI/CD po klienta instytucjonalnego. Szerokie zaplecze
inżynierskie: Linux/sieci (klaster HPC, Cisco CCNA), dwa lata rozwoju oprogramowania
naukowego w Pythonie (UMK) oraz embedded/IoT (Raspberry Pi). Doprowadzam projekty do końca
niezależnie od tego, czy bariera jest techniczna, biznesowa czy formalna: od zera do
produkcji w 3 miesiące, wygrana w konkursie startupowym (Copernicus Startup Stars 2026)
i zdany audyt bezpieczeństwa instytucji publicznej.

**EN:** Single-handedly designed, built, and shipped to production a commercial
self-service printing system (.NET 8, React 19 / TypeScript, Azure) — from concept and
code through payments, cloud, and CI/CD to an institutional client. Broad engineering
background: Linux/networking (HPC cluster, Cisco CCNA), two years of scientific-software
development in Python (NCU), and embedded/IoT (Raspberry Pi). Delivers projects to the
finish whether the barrier is technical, business, or formal: zero to production in 3
months, a startup-competition win (Copernicus Startup Stars 2026), and a passed
public-institution security audit.

## Tech stack
- **Backend:** C#, ASP.NET Core 8, Entity Framework Core, REST API, WebSocket · Node.js, NestJS · Python (FastAPI)
- **Frontend:** React 19, TypeScript, JavaScript, Vite, Tailwind CSS, i18n, accessibility (a11y)
- **Cloud / DevOps:** Microsoft Azure (App Service, SQL Database, Service Bus, Blob Storage, Key Vault, Virtual Network, Managed Identity, Application Insights), Azure CLI, GitHub Actions (CI/CD, OIDC), Docker, Docker Compose
- **Linux / networking:** bash automation, HPC cluster, PBS, conda, network admin (AP, DHCP, DNS, NAT, SSH), Cisco CCNA
- **Databases:** Azure SQL, SQLite (EF Core), MongoDB
- **Security:** defense-in-depth, threat modeling, Managed Identity + Key Vault, GDPR (privacy by design)
- **Python / AI / data:** NumPy, SciPy, pandas, matplotlib, Jupyter, scikit-learn, LLM integration into applications · Psi4
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
### DrukMruk — Founder & Lead Developer · 02.2026 – present · drukmruk.pl
- Od zera do produkcji w 3 miesiące, solo — komercyjny, rozproszony system druku samoobsługowego dla środowiska akademickiego: web app (React 19 / TypeScript), backend chmurowy (ASP.NET Core 8, Azure) i sieć fizycznych kiosków IoT (Raspberry Pi).
- Zdany miesięczny audyt bezpieczeństwa instytucji publicznej (UCI UMK) — obrona architektury i hardening (izolacja sieciowa warstw, ochrona danych, centralne logowanie i alertowanie incydentów).
- Cały backend chmurowy z odporną na błędy integracją płatności (Autopay) — kryptograficznie weryfikowane webhooki, automatyczne zwroty, gwarantowana spójność stanu; krytyczne przepływy pokryte testami (TDD); CI/CD w GitHub Actions z federacją OIDC.
- Autonomiczne kioski druku działające bezobsługowo w przestrzeni publicznej — Raspberry Pi 5 z ekranem dotykowym i lokalnym agentem (FastAPI), dedykowane LTE, pełna izolacja od sieci uczelni, warstwowy hardening (defense-in-depth).
- Wygrana Copernicus Startup Stars 2026 i oficjalna zgoda uczelni na wdrożenie kiosków — przeprowadzenie projektu przez negocjacje z władzami UMK, dokumentację techniczną i pełną ścieżkę formalno-prawną.

### Uniwersytet Mikołaja Kopernika w Toruniu (UMK) — Scientific programmer (quantum chemistry) · 02.2024 – 03.2026
- Zaprojektowanie i napisanie biblioteki obliczeniowej w Pythonie używanej przez całą grupę badawczą — modularna architektura przyspieszająca obliczenia względem metod tej samej klasy dokładności, łatwo rozszerzalna; przygotowywana do publikacji open-source.
- Automatyzacja cyklu obliczeniowego na klastrze — skrócenie partii obliczeń z ~doby do godziny; skrypty do kolejkowania, uruchamiania zadań i monitoringu zasobów; konfiguracja środowisk (Linux, conda, PBS).
- Weryfikacja poprawności metody względem literatury i danych referencyjnych — analiza numeryczna (NumPy), wizualizacje, porównania do publikacji.

## Projects
### Ventilator simulator (Respirator-simulator) — Team leader · 2026
https://github.com/yanlukashevich/Respirator-simulator
- Poprowadzenie 4-osobowego zespołu do 1. miejsca w konkursie Instytutu Fizyki UMK i statusu laureata w konkursie ogólnouczelnianym — rozproszony symulator respiratora w czasie rzeczywistym; projekt wchodzi w komercjalizację jako spółka spin-off UMK.
- Przełożenie wymagań medycznych na specyfikację i architekturę — fizyczne stanowiska pacjenta (Raspberry Pi, pokrętła) i panel trenera; integracja komponentów (Node.js / NestJS, WebSocket, React, Raspberry Pi).
- Zaprojektowanie sieci skalującej system z 2 do 15 stanowisk — zbudowanej od zera (Linux, AP / DHCP / DNS / NAT / SSH).

## Education
- Informatyka Stosowana, studia inżynierskie (inż.) — Uniwersytet Mikołaja Kopernika w Toruniu, 2022 – 2026

## Certificates
- Cisco CCNA

## Why-me material (raw points for free-text answers)
- Dowożę od zera do produkcji — komercyjny system .NET 8 / React / Azure wdrożony solo w 3 miesiące dla klienta instytucjonalnego.
- Full-stack end-to-end: frontend (React/TS), backend (ASP.NET Core / FastAPI), chmura (Azure), CI/CD (GitHub Actions, OIDC), płatności, bezpieczeństwo.
- Zdany audyt bezpieczeństwa instytucji publicznej — realny threat modeling i hardening, nie teoria.
- Zaplecze naukowe w Pythonie (2 lata, UMK) — biblioteka obliczeniowa dla całej grupy badawczej, automatyzacja klastra HPC.
- Prowadzę zespoły i projekty do wyniku — 1. miejsce w konkursie, laureat, wejście w komercjalizację (spin-off).
- Doprowadzam rzeczy do końca niezależnie od bariery: technicznej, biznesowej czy formalnej.

## CV variants
Files under `CV_PDF/`. Default variant = **universal**.

| Offer stack | PL file | EN file |
|-------------|---------|---------|
| python | `CV_PDF/CV_Yan_Lukashevich_python/CV_Yan_Lukashevich.pdf` | `CV_PDF/CV_Yan_Lukashevich_python/CV_Yan_Lukashevich_EN.pdf` |
| dotnet | `CV_PDF/CV_Yan_Lukashevich_dotnet_fullstack/CV_Yan_Lukashevich.pdf` | `CV_PDF/CV_Yan_Lukashevich_dotnet_fullstack/CV_Yan_Lukashevich_EN.pdf` |
| cloud / devops | `CV_PDF/CV_Yan_Lukashevich_cloud_devops/CV_Yan_Lukashevich.pdf` | `CV_PDF/CV_Yan_Lukashevich_cloud_devops/CV_Yan_Lukashevich_EN.pdf` |
| universal (default) | `CV_PDF/CV_Yan_Lukashevich_universal/CV_Yan_Lukashevich.pdf` | `CV_PDF/CV_Yan_Lukashevich_universal/CV_Yan_Lukashevich_EN.pdf` |
