from bs4 import BeautifulSoup

from audyt_sklepu.checks import (
    audytuj_strone,
    czy_karta_produktu,
    sprawdz_alt_obrazkow,
    sprawdz_h1,
    sprawdz_karte_produktu,
    sprawdz_meta_description,
    sprawdz_serwis,
    sprawdz_title,
)
from audyt_sklepu.models import Strona, Waga

DOBRY_PRODUKT = """
<html><head>
  <title>Kubek ceramiczny 350 ml - niebieski | Sklep Przykład</title>
  <meta name="description" content="Ręcznie malowany kubek ceramiczny 350 ml. Można myć w zmywarce i podgrzewać w mikrofalówce. Wysyłka w 24h.">
  <script type="application/ld+json">
  {"@context": "https://schema.org", "@type": "Product", "name": "Kubek ceramiczny",
   "image": "https://example.com/kubek.jpg",
   "description": "Ręcznie malowany kubek ceramiczny o pojemności 350 ml, wykonany z wysokiej jakości kamionki. Idealny na kawę i herbatę.",
   "offers": {"@type": "Offer", "price": "49.00", "priceCurrency": "PLN"}}
  </script>
</head><body>
  <h1>Kubek ceramiczny 350 ml</h1>
  <img src="kubek.jpg" alt="Niebieski kubek ceramiczny">
  <table><tr><th>EAN</th><td>5901234123457</td></tr></table>
  <button>Dodaj do koszyka</button>
</body></html>
"""


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def kody(problemy) -> set[str]:
    return {p.kod for p in problemy}


def test_dobra_karta_produktu_nie_ma_problemow():
    strona = Strona(url="https://example.com/kubek", status=200, czas_odpowiedzi=0.3, html=DOBRY_PRODUKT)
    audytuj_strone(strona)
    assert strona.czy_produkt
    assert strona.problemy == []
    assert strona.wynik == 100


def test_brak_title_jest_krytyczny():
    problemy = sprawdz_title(soup("<html><head></head></html>"))
    assert kody(problemy) == {"brak-title"}
    assert problemy[0].waga is Waga.KRYTYCZNY


def test_za_dlugi_title():
    assert kody(sprawdz_title(soup(f"<title>{'a' * 80}</title>"))) == {"dlugi-title"}


def test_brak_meta_description():
    assert kody(sprawdz_meta_description(soup("<head></head>"))) == {"brak-meta-description"}


def test_brak_i_wiele_h1():
    assert kody(sprawdz_h1(soup("<body></body>"))) == {"brak-h1"}
    assert kody(sprawdz_h1(soup("<h1>a</h1><h1>b</h1>"))) == {"wiele-h1"}


def test_obrazki_bez_alt_sa_liczone():
    problemy = sprawdz_alt_obrazkow(soup('<img src="a.jpg"><img src="b.jpg" alt=" "><img src="c.jpg" alt="ok">'))
    assert kody(problemy) == {"obrazki-bez-alt"}
    assert "2 obrazków" in problemy[0].opis


def test_rozpoznaje_karte_produktu_po_og_type_i_microdata():
    assert czy_karta_produktu(soup('<meta property="og:type" content="product">'))
    assert czy_karta_produktu(soup('<div itemscope itemtype="https://schema.org/Product"></div>'))
    assert not czy_karta_produktu(soup("<a href='/kontakt'>Kontakt</a>"))


def test_lista_produktow_to_nie_karta_produktu():
    # Kategoria z jednym albo wieloma produktami - przyciski koszyka nie wystarczą.
    for liczba in (1, 20):
        kategoria = "<ul>" + "<li>Książka <button>Add to basket</button></li>" * liczba + "</ul>"
        assert not czy_karta_produktu(soup(kategoria))


def test_rozpoznaje_karte_produktu_po_kodzie():
    assert czy_karta_produktu(soup("<table><tr><th>UPC</th><td>a897fe39b1053632</td></tr></table>"))
    assert czy_karta_produktu(soup("<dl><dt>Kod produktu:</dt><dd>KB-350</dd></dl>"))


def test_produkt_bez_danych_strukturalnych():
    assert kody(sprawdz_karte_produktu(soup("<th>SKU</th>"))) == {"brak-schema-product"}


def test_produkt_z_niepelnymi_danymi_strukturalnymi():
    html = '<script type="application/ld+json">{"@type": "Product", "name": "X"}</script>'
    assert kody(sprawdz_karte_produktu(soup(html))) == {
        "schema-bez-ceny", "schema-bez-zdjecia", "krotki-opis-produktu",
    }


def test_blad_http_i_brak_odpowiedzi():
    s404 = Strona(url="https://example.com/x", status=404, czas_odpowiedzi=0.1)
    audytuj_strone(s404)
    assert kody(s404.problemy) == {"blad-http"}

    timeout = Strona(url="https://example.com/y", status=0, czas_odpowiedzi=15)
    audytuj_strone(timeout)
    assert kody(timeout.problemy) == {"brak-odpowiedzi"}


def test_wolna_strona():
    strona = Strona(url="https://example.com", status=200, czas_odpowiedzi=3.5, html=DOBRY_PRODUKT)
    audytuj_strone(strona)
    assert "wolna-strona" in kody(strona.problemy)


def test_problemy_calego_serwisu():
    strony = [Strona(url=f"https://example.com/{i}", status=200, czas_odpowiedzi=0.1, tytul="Sklep") for i in range(3)]
    problemy = sprawdz_serwis(strony, https=False, ma_robots=False, ma_sitemap=False)
    assert kody(problemy) == {"brak-https", "brak-robots", "brak-sitemap", "zduplikowane-title"}
