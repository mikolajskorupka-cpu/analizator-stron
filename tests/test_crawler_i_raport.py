from audyt_sklepu.crawler import linki_wewnetrzne, normalizuj
from audyt_sklepu.models import Audyt, Problem, Strona, Waga
from audyt_sklepu.report import do_slownika, grupuj, render_html


def test_normalizuj_usuwa_kotwice_i_ukosnik():
    assert normalizuj("https://sklep.pl/kategoria/#opis") == "https://sklep.pl/kategoria"
    assert normalizuj("https://sklep.pl/") == "https://sklep.pl/"


def test_linki_wewnetrzne_tylko_z_tej_samej_domeny():
    html = """
      <a href="/produkt/1">P1</a>
      <a href="produkt/2#opinie">P2</a>
      <a href="https://inna-domena.pl/x">obcy</a>
      <a href="/zdjecie.jpg">plik</a>
      <a href="mailto:kontakt@sklep.pl">mail</a>
    """
    assert linki_wewnetrzne(html, "https://sklep.pl/kategoria/") == [
        "https://sklep.pl/produkt/1",
        "https://sklep.pl/kategoria/produkt/2",
    ]


def _audyt_przykladowy() -> Audyt:
    brak_h1 = Problem("brak-h1", Waga.WAZNY, "Brak H1", "Dodaj H1")
    audyt = Audyt(adres_startowy="https://sklep.pl")
    audyt.strony = [
        Strona(url="https://sklep.pl/a", status=200, czas_odpowiedzi=0.2, tytul="A", problemy=[brak_h1]),
        Strona(url="https://sklep.pl/b", status=200, czas_odpowiedzi=0.2, tytul="B <script>", problemy=[brak_h1]),
    ]
    audyt.problemy_serwisu = [Problem("brak-https", Waga.KRYTYCZNY, "Brak HTTPS", "Włącz SSL")]
    return audyt


def test_wynik_i_grupowanie():
    audyt = _audyt_przykladowy()
    assert audyt.wynik == 65  # średnia 90 minus 25 za brak HTTPS
    grupy = grupuj(audyt)
    assert [g.problem.kod for g in grupy] == ["brak-https", "brak-h1"]
    assert len(grupy[1].adresy) == 2


def test_raporty_html_i_json():
    audyt = _audyt_przykladowy()
    html = render_html(audyt)
    assert "65/100" in html
    assert "B &lt;script&gt;" in html  # tekst ze strony jest bezpiecznie zakodowany
    dane = do_slownika(audyt)
    assert dane["wynik"] == 65
    assert dane["problemy"][0]["kod"] == "brak-https"
