"""Reguły audytu.

Każda reguła dostaje sparsowaną stronę i zwraca listę znalezionych problemów.
Reguły nie łączą się z internetem, dzięki czemu łatwo je testować.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

from bs4 import BeautifulSoup

from .models import Problem, Strona, Waga

# Etykiety w tabeli parametrów, po których rozpoznajemy kartę produktu.
KOD_PRODUKTU = re.compile(r"(SKU|EAN|UPC|GTIN|kod produktu|nr katalogowy):?", re.I)

WOLNA_ODPOWIEDZ_S = 2.0


def dane_strukturalne(soup: BeautifulSoup) -> list[dict]:
    """Zwraca obiekty JSON-LD (schema.org) zapisane w stronie."""
    obiekty: list[dict] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            dane = json.loads(tag.string or "")
        except json.JSONDecodeError:
            continue
        kandydaci = dane if isinstance(dane, list) else dane.get("@graph", [dane])
        obiekty.extend(o for o in kandydaci if isinstance(o, dict))
    return obiekty


def produkt_ld(soup: BeautifulSoup) -> dict | None:
    for obiekt in dane_strukturalne(soup):
        typ = obiekt.get("@type")
        typy = typ if isinstance(typ, list) else [typ]
        if "Product" in typy:
            return obiekt
    return None


def czy_karta_produktu(soup: BeautifulSoup) -> bool:
    """Zgaduje, czy strona to karta produktu (a nie np. lista produktów w kategorii)."""
    if produkt_ld(soup):
        return True
    og_type = soup.find("meta", property="og:type")
    if og_type and og_type.get("content", "").lower() == "product":
        return True
    if soup.find(attrs={"itemtype": re.compile(r"schema\.org/Product$", re.I)}):
        return True
    # Przycisk "do koszyka" nic nie mówi - bywa też przy każdym produkcie na liście
    # w kategorii. Za to tabela parametrów z kodem (SKU, EAN...) zdradza kartę produktu.
    for el in soup.find_all(["th", "dt", "label", "span", "td"]):
        if KOD_PRODUKTU.fullmatch(el.get_text(" ", strip=True)):
            return True
    return False


def sprawdz_title(soup: BeautifulSoup) -> list[Problem]:
    tytul = soup.title.get_text(strip=True) if soup.title else ""
    if not tytul:
        return [Problem("brak-title", Waga.KRYTYCZNY, "Strona nie ma tytułu (<title>).",
                        "Dodaj unikalny tytuł z nazwą produktu/kategorii i marką sklepu.")]
    if len(tytul) < 15:
        return [Problem("krotki-title", Waga.DROBNY, f"Tytuł jest bardzo krótki ({len(tytul)} znaków).",
                        "Rozbuduj tytuł do 30-60 znaków, dodając słowa, które wpisują klienci.")]
    if len(tytul) > 65:
        return [Problem("dlugi-title", Waga.DROBNY, f"Tytuł jest za długi ({len(tytul)} znaków) - Google go utnie.",
                        "Skróć tytuł do ok. 60 znaków; najważniejsze słowa daj na początek.")]
    return []


def sprawdz_meta_description(soup: BeautifulSoup) -> list[Problem]:
    meta = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    opis = (meta.get("content") or "").strip() if meta else ""
    if not opis:
        return [Problem("brak-meta-description", Waga.WAZNY, "Brak opisu meta (meta description).",
                        "Dodaj 120-160 znaków zachęcających do kliknięcia w wynikach Google.")]
    if len(opis) > 170:
        return [Problem("dlugi-meta-description", Waga.DROBNY, f"Opis meta ma {len(opis)} znaków - zostanie ucięty.",
                        "Skróć opis do ok. 160 znaków.")]
    return []


def sprawdz_h1(soup: BeautifulSoup) -> list[Problem]:
    naglowki = soup.find_all("h1")
    if not naglowki:
        return [Problem("brak-h1", Waga.WAZNY, "Strona nie ma nagłówka H1.",
                        "Dodaj jeden nagłówek H1 z główną nazwą produktu lub kategorii.")]
    if len(naglowki) > 1:
        return [Problem("wiele-h1", Waga.DROBNY, f"Strona ma {len(naglowki)} nagłówki H1.",
                        "Zostaw jeden H1, pozostałe zamień na H2/H3.")]
    return []


def sprawdz_alt_obrazkow(soup: BeautifulSoup) -> list[Problem]:
    bez_alt = [img for img in soup.find_all("img") if not (img.get("alt") or "").strip()]
    if not bez_alt:
        return []
    return [Problem("obrazki-bez-alt", Waga.DROBNY, f"{len(bez_alt)} obrazków nie ma opisu alternatywnego (alt).",
                    "Dodaj alt opisujący produkt - pomaga w Google Grafika i osobom niewidomym.")]


def sprawdz_karte_produktu(soup: BeautifulSoup) -> list[Problem]:
    """Reguły tylko dla kart produktów."""
    produkt = produkt_ld(soup)
    if produkt is None:
        return [Problem("brak-schema-product", Waga.WAZNY,
                        "Karta produktu nie ma danych strukturalnych Product (schema.org).",
                        "Dodaj JSON-LD Product z ceną, dostępnością i zdjęciem - "
                        "Google pokaże wtedy cenę i gwiazdki w wynikach wyszukiwania.")]
    problemy = []
    oferta = produkt.get("offers")
    oferta = oferta[0] if isinstance(oferta, list) and oferta else oferta
    if not isinstance(oferta, dict) or "price" not in oferta:
        problemy.append(Problem("schema-bez-ceny", Waga.WAZNY, "Dane strukturalne produktu nie zawierają ceny.",
                                "Uzupełnij offers.price i offers.priceCurrency w JSON-LD."))
    if not produkt.get("image"):
        problemy.append(Problem("schema-bez-zdjecia", Waga.DROBNY, "Dane strukturalne produktu nie zawierają zdjęcia.",
                                "Uzupełnij pole image w JSON-LD."))
    if len(str(produkt.get("description", ""))) < 100:
        problemy.append(Problem("krotki-opis-produktu", Waga.WAZNY, "Opis produktu jest bardzo krótki lub go brak.",
                                "Napisz opis min. 300 znaków: zastosowanie, materiał, wymiary, korzyści."))
    return problemy


def sprawdz_odpowiedz(strona: Strona) -> list[Problem]:
    if strona.status == 0:
        return [Problem("brak-odpowiedzi", Waga.KRYTYCZNY, "Strona nie odpowiedziała (błąd połączenia lub timeout).",
                        "Sprawdź, czy serwer działa i czy strona nie ładuje się zbyt długo.")]
    if strona.status >= 400:
        return [Problem("blad-http", Waga.KRYTYCZNY, f"Strona zwraca błąd HTTP {strona.status}.",
                        "Napraw stronę albo ustaw przekierowanie 301 i usuń linki prowadzące do niej.")]
    if strona.czas_odpowiedzi > WOLNA_ODPOWIEDZ_S:
        return [Problem("wolna-strona", Waga.WAZNY, f"Serwer odpowiadał {strona.czas_odpowiedzi:.1f} s.",
                        "Sprawdź hosting, cache i wielkość strony - klienci odchodzą po ok. 3 s czekania.")]
    return []


REGULY_STRONY = [sprawdz_title, sprawdz_meta_description, sprawdz_h1, sprawdz_alt_obrazkow]


def audytuj_strone(strona: Strona) -> None:
    """Uzupełnia stronę o tytuł, typ i listę problemów."""
    strona.problemy = sprawdz_odpowiedz(strona)
    if strona.status == 0 or strona.status >= 400 or not strona.html:
        return
    soup = BeautifulSoup(strona.html, "html.parser")
    strona.tytul = soup.title.get_text(strip=True) if soup.title else ""
    strona.czy_produkt = czy_karta_produktu(soup)
    for regula in REGULY_STRONY:
        strona.problemy.extend(regula(soup))
    if strona.czy_produkt:
        strona.problemy.extend(sprawdz_karte_produktu(soup))


def sprawdz_serwis(strony: list[Strona], https: bool, ma_robots: bool, ma_sitemap: bool) -> list[Problem]:
    """Reguły dotyczące całego sklepu, a nie pojedynczej strony."""
    problemy = []
    if not https:
        problemy.append(Problem("brak-https", Waga.KRYTYCZNY, "Sklep nie działa na HTTPS.",
                                "Włącz certyfikat SSL - przeglądarki oznaczają taki sklep jako niebezpieczny."))
    if not ma_robots:
        problemy.append(Problem("brak-robots", Waga.DROBNY, "Brak pliku robots.txt.",
                                "Dodaj robots.txt ze wskazaniem mapy strony."))
    if not ma_sitemap:
        problemy.append(Problem("brak-sitemap", Waga.WAZNY, "Nie znaleziono mapy strony (sitemap.xml).",
                                "Wygeneruj sitemap.xml, żeby Google szybciej znajdował nowe produkty."))

    po_tytule: dict[str, list[str]] = defaultdict(list)
    for s in strony:
        if s.tytul:
            po_tytule[s.tytul].append(s.url)
    duplikaty = {t: urle for t, urle in po_tytule.items() if len(urle) > 1}
    if duplikaty:
        przyklad = next(iter(duplikaty))
        stron = sum(len(urle) for urle in duplikaty.values())
        problemy.append(Problem("zduplikowane-title", Waga.WAZNY,
                                f"Powtarzające się tytuły na {stron} stronach (np. „{przyklad}”).",
                                "Każda strona powinna mieć unikalny tytuł - inaczej Google nie wie, którą pokazać."))
    return problemy
