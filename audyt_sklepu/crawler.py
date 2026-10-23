"""Pobieranie stron sklepu (crawler).

Zaczynamy od adresu startowego i idziemy po linkach wewnątrz tej samej domeny,
aż zbierzemy `max_stron` stron. Szanujemy robots.txt i robimy przerwy między
zapytaniami, żeby nie obciążać cudzego serwera.
"""

from __future__ import annotations

import time
from collections import deque
from urllib.parse import urldefrag, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from . import __version__
from .models import Strona

USER_AGENT = f"AudytSklepu/{__version__} (+https://github.com/mikolajskorupka-cpu/analizator-stron)"

POMIJANE_ROZSZERZENIA = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".pdf", ".zip",
    ".css", ".js", ".ico", ".mp4", ".xml", ".txt",
)


def normalizuj(url: str) -> str:
    """Usuwa #kotwice i końcowy ukośnik, żeby nie odwiedzać tej samej strony dwa razy."""
    url, _ = urldefrag(url)
    return url.rstrip("/") if urlparse(url).path not in ("", "/") else url


def linki_wewnetrzne(html: str, adres_strony: str) -> list[str]:
    """Zwraca linki z tej samej domeny, które wyglądają na strony HTML."""
    domena = urlparse(adres_strony).netloc
    soup = BeautifulSoup(html, "html.parser")
    wynik = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        pelny = normalizuj(urljoin(adres_strony, href))
        czesci = urlparse(pelny)
        if czesci.scheme not in ("http", "https") or czesci.netloc != domena:
            continue
        if czesci.path.lower().endswith(POMIJANE_ROZSZERZENIA):
            continue
        wynik.append(pelny)
    return wynik


class Crawler:
    def __init__(self, adres_startowy: str, max_stron: int = 50, przerwa: float = 0.5, timeout: float = 15):
        self.adres_startowy = normalizuj(adres_startowy)
        self.max_stron = max_stron
        self.przerwa = przerwa
        self.timeout = timeout
        self.sesja = requests.Session()
        self.sesja.headers["User-Agent"] = USER_AGENT
        czesci = urlparse(self.adres_startowy)
        self.korzen = f"{czesci.scheme}://{czesci.netloc}"
        self.robots = RobotFileParser()
        self.ma_robots = False

    def _wczytaj_robots(self) -> None:
        try:
            odp = self.sesja.get(f"{self.korzen}/robots.txt", timeout=self.timeout)
        except requests.RequestException:
            odp = None
        if odp is not None and odp.ok:
            self.ma_robots = True
            self.robots.parse(odp.text.splitlines())
        else:
            self.robots.parse([])  # brak robots.txt = wszystko dozwolone

    def ma_sitemap(self) -> bool:
        adresy = list(self.robots.site_maps() or []) or [f"{self.korzen}/sitemap.xml"]
        for adres in adresy:
            try:
                if self.sesja.get(adres, timeout=self.timeout).ok:
                    return True
            except requests.RequestException:
                pass
        return False

    def pobierz(self, url: str) -> Strona:
        start = time.perf_counter()
        try:
            odp = self.sesja.get(url, timeout=self.timeout)
        except requests.RequestException:
            return Strona(url=url, status=0, czas_odpowiedzi=time.perf_counter() - start)
        czas = time.perf_counter() - start
        typ = odp.headers.get("Content-Type", "")
        html = odp.text if "html" in typ else ""
        return Strona(url=url, status=odp.status_code, czas_odpowiedzi=czas, html=html)

    def przeszukaj(self, przy_stronie=None) -> list[Strona]:
        """Odwiedza strony wszerz (najpierw te najbliżej strony głównej)."""
        self._wczytaj_robots()
        kolejka = deque([self.adres_startowy])
        widziane = {self.adres_startowy}
        strony: list[Strona] = []
        while kolejka and len(strony) < self.max_stron:
            url = kolejka.popleft()
            if not self.robots.can_fetch(USER_AGENT, url):
                continue
            strona = self.pobierz(url)
            strony.append(strona)
            if przy_stronie:
                przy_stronie(strona, len(strony))
            for link in linki_wewnetrzne(strona.html, url) if strona.html else []:
                if link not in widziane:
                    widziane.add(link)
                    kolejka.append(link)
            time.sleep(self.przerwa)
        return strony
