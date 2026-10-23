# Audyt sklepu internetowego 🛒🔍

Narzędzie w Pythonie, które **automatycznie sprawdza sklep internetowy** i tworzy czytelny raport z problemami, które kosztują sklep klientów i pozycje w Google: braki w SEO, niekompletne karty produktów, błędy techniczne.

Jeden przebieg zastępuje kilka godzin ręcznego klikania po sklepie. Raport HTML można od razu wysłać właścicielowi sklepu.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Testy](https://img.shields.io/badge/testy-pytest-green)

## Problem biznesowy

Właściciele małych i średnich sklepów rzadko wiedzą, że:
- połowa ich kart produktów nie ma opisu meta, więc Google wstawia w wynikach przypadkowy tekst,
- brak danych strukturalnych `Product` (schema.org) oznacza **brak ceny i gwiazdek** w wynikach wyszukiwania,
- niektóre strony zwracają błąd 404 albo ładują się kilka sekund.

Ręczne sprawdzenie 50 stron zajmuje godziny. To narzędzie robi to w minutę.

## Co sprawdza

| Obszar | Reguły |
|---|---|
| **SEO stron** | brak / zbyt krótki / zbyt długi `<title>`, brak lub za długi meta description, brak lub wiele nagłówków H1, obrazki bez `alt` |
| **Karty produktów** | dane strukturalne schema.org `Product`: cena, zdjęcie, opis (min. 100 znaków) |
| **Technika** | błędy HTTP (4xx/5xx), brak odpowiedzi, wolna odpowiedź serwera (> 2 s) |
| **Cały sklep** | HTTPS, `robots.txt`, `sitemap.xml`, powtarzające się tytuły stron |

Każdy problem ma **wagę** (krytyczny / ważny / drobny) i **konkretną rekomendację**, co zrobić. Sklep dostaje ocenę 0–100.

## Przykładowy wynik

Audyt ćwiczebnego sklepu [books.toscrape.com](https://books.toscrape.com) (80 stron, 25 kart produktów):

```
Ocena ogólna: 66/100

ważny  | Brak opisu meta (meta description)                      | 55 stron
ważny  | Karta produktu nie ma danych strukturalnych Product     | 25 stron
ważny  | Nie znaleziono mapy strony (sitemap.xml)                | cały sklep
ważny  | Powtarzające się tytuły na 5 stronach                   | cały sklep
drobny | Opis meta jest za długi - zostanie ucięty               | 25 stron
drobny | Tytuł jest za długi - Google go utnie                   | 10 stron
drobny | Brak pliku robots.txt                                   | cały sklep
```

👉 **[Zobacz pełny raport HTML w przeglądarce](https://mikolajskorupka-cpu.github.io/analizator-stron/przyklady/audyt-books.toscrape.com.html)** · [raport JSON](przyklady/audyt-books.toscrape.com.json)

## Jak uruchomić

Wymagany Python 3.10 lub nowszy.

```bash
git clone https://github.com/mikolajskorupka-cpu/analizator-stron.git
cd analizator-stron
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt

python -m audyt_sklepu https://adres-sklepu.pl
```

Opcje:

| Opcja | Domyślnie | Opis |
|---|---|---|
| `--max-stron` | 50 | ile stron sprawdzić |
| `--przerwa` | 0.5 | przerwa między zapytaniami (s), żeby nie obciążać serwera sklepu |
| `--wyjscie` | `raporty` | folder na raporty HTML i JSON |

## Jak to działa

```
adres sklepu
     │
     ▼
crawler.py ── pobiera strony po linkach wewnętrznych (wszerz, szanuje robots.txt)
     │
     ▼
checks.py ─── reguły: każda dostaje stronę i zwraca listę problemów
     │
     ▼
report.py ─── grupuje problemy, liczy ocenę, zapisuje raport HTML i JSON
```

| Plik | Odpowiada za |
|---|---|
| `audyt_sklepu/crawler.py` | pobieranie stron, filtrowanie linków, robots.txt, sitemap |
| `audyt_sklepu/checks.py` | reguły audytu i rozpoznawanie kart produktów |
| `audyt_sklepu/models.py` | struktury danych (`Strona`, `Problem`, `Audyt`) i liczenie oceny |
| `audyt_sklepu/report.py` | raport HTML (dla człowieka) i JSON (dla innych programów) |
| `audyt_sklepu/__main__.py` | uruchamianie z terminala |

Decyzje projektowe:
- **Reguły nie łączą się z internetem.** Dostają gotowy HTML, dzięki czemu testy są szybkie i nie zależą od cudzych stron.
- **Karty produktów są rozpoznawane po danych, nie po przyciskach.** Przycisk „Do koszyka” występuje też na listach w kategoriach, więc narzędzie patrzy na schema.org `Product`, `og:type` i kody produktu (SKU/EAN/UPC).
- **Kulturalny crawler:** własny User-Agent, przestrzeganie `robots.txt`, przerwy między zapytaniami.

## Testy

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## Plany rozwoju

- [ ] ocena szybkości ładowania przez Google PageSpeed API
- [ ] wykrywanie zepsutych linków i zdjęć
- [ ] porównanie dwóch audytów (co się poprawiło od ostatniego razu)
- [ ] podsumowanie raportu napisane przez AI (Claude) w języku zrozumiałym dla właściciela sklepu
