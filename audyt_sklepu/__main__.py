"""Uruchamianie z terminala:  python -m audyt_sklepu https://adres-sklepu.pl"""

from __future__ import annotations

import argparse
import os
import sys
from urllib.parse import urlparse

from .checks import audytuj_strone, sprawdz_serwis
from .crawler import Crawler
from .models import Audyt
from .report import zapisz_html, zapisz_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="audyt_sklepu",
        description="Sprawdza sklep internetowy pod kątem SEO, kart produktów i problemów technicznych.",
    )
    parser.add_argument("adres", help="adres sklepu, np. https://books.toscrape.com")
    parser.add_argument("--max-stron", type=int, default=50, help="ile stron sprawdzić (domyślnie 50)")
    parser.add_argument("--przerwa", type=float, default=0.5, help="przerwa między zapytaniami w sekundach")
    parser.add_argument("--wyjscie", default="raporty", help="folder na raporty (domyślnie: raporty)")
    args = parser.parse_args(argv)

    if not urlparse(args.adres).scheme:
        args.adres = "https://" + args.adres

    print(f"Audyt: {args.adres} (max {args.max_stron} stron)")
    crawler = Crawler(args.adres, max_stron=args.max_stron, przerwa=args.przerwa)

    def postep(strona, numer):
        print(f"  [{numer:>3}] {strona.status or 'BŁĄD'}  {strona.url}")

    audyt = Audyt(adres_startowy=crawler.adres_startowy)
    audyt.strony = crawler.przeszukaj(przy_stronie=postep)
    if not audyt.strony:
        print("Nie udało się pobrać żadnej strony (sprawdź adres i robots.txt).", file=sys.stderr)
        return 1

    for strona in audyt.strony:
        audytuj_strone(strona)
    audyt.problemy_serwisu = sprawdz_serwis(
        audyt.strony,
        https=crawler.adres_startowy.startswith("https://"),
        ma_robots=crawler.ma_robots,
        ma_sitemap=crawler.ma_sitemap(),
    )

    os.makedirs(args.wyjscie, exist_ok=True)
    nazwa = urlparse(crawler.adres_startowy).netloc.replace(":", "_")
    sciezka_html = os.path.join(args.wyjscie, f"audyt-{nazwa}.html")
    sciezka_json = os.path.join(args.wyjscie, f"audyt-{nazwa}.json")
    zapisz_html(audyt, sciezka_html)
    zapisz_json(audyt, sciezka_json)

    print(f"\nOcena ogólna: {audyt.wynik}/100")
    print(f"Raport HTML: {sciezka_html}")
    print(f"Raport JSON: {sciezka_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
