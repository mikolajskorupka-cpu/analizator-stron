"""Tworzenie raportu z audytu: HTML dla klienta i JSON dla innych programów."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from html import escape

from .models import Audyt, Problem, Waga

KOLEJNOSC_WAG = [Waga.KRYTYCZNY, Waga.WAZNY, Waga.DROBNY]


@dataclass
class GrupaProblemow:
    """Ten sam problem zebrany ze wszystkich stron, na których wystąpił."""

    problem: Problem
    adresy: list[str] = field(default_factory=list)


def grupuj(audyt: Audyt) -> list[GrupaProblemow]:
    grupy: dict[str, GrupaProblemow] = {}
    for p in audyt.problemy_serwisu:
        grupy[p.kod] = GrupaProblemow(p, [audyt.adres_startowy])
    for strona in audyt.strony:
        for p in strona.problemy:
            grupy.setdefault(p.kod, GrupaProblemow(p)).adresy.append(strona.url)
    # Najpierw najpoważniejsze, potem te, które dotyczą najwięcej stron.
    return sorted(grupy.values(), key=lambda g: (KOLEJNOSC_WAG.index(g.problem.waga), -len(g.adresy)))


def do_slownika(audyt: Audyt) -> dict:
    return {
        "adres": audyt.adres_startowy,
        "data": date.today().isoformat(),
        "wynik": audyt.wynik,
        "liczba_stron": len(audyt.strony),
        "liczba_kart_produktow": sum(s.czy_produkt for s in audyt.strony),
        "problemy": [
            {
                "kod": g.problem.kod,
                "waga": g.problem.waga.value,
                "opis": g.problem.opis,
                "rekomendacja": g.problem.rekomendacja,
                "liczba_stron": len(g.adresy),
                "adresy": g.adresy,
            }
            for g in grupuj(audyt)
        ],
        "strony": [
            {
                "url": s.url,
                "status": s.status,
                "czas_odpowiedzi_s": round(s.czas_odpowiedzi, 2),
                "tytul": s.tytul,
                "karta_produktu": s.czy_produkt,
                "wynik": s.wynik,
                "problemy": [p.kod for p in s.problemy],
            }
            for s in audyt.strony
        ],
    }


def zapisz_json(audyt: Audyt, sciezka: str) -> None:
    with open(sciezka, "w", encoding="utf-8") as f:
        json.dump(do_slownika(audyt), f, ensure_ascii=False, indent=2)


def _kolor_wyniku(wynik: int) -> str:
    return "dobry" if wynik >= 80 else "sredni" if wynik >= 50 else "slaby"


def render_html(audyt: Audyt) -> str:
    grupy = grupuj(audyt)
    licznik = {w: sum(1 for g in grupy if g.problem.waga == w) for w in KOLEJNOSC_WAG}

    karty_problemow = []
    for g in grupy:
        adresy = "".join(f'<li><a href="{escape(u)}">{escape(u)}</a></li>' for u in g.adresy[:10])
        reszta = f"<li>…i {len(g.adresy) - 10} więcej</li>" if len(g.adresy) > 10 else ""
        karty_problemow.append(f"""
        <article class="problem {g.problem.waga.name.lower()}">
          <header><span class="waga">{escape(g.problem.waga.value)}</span>
            <h3>{escape(g.problem.opis)}</h3></header>
          <p><strong>Co zrobić:</strong> {escape(g.problem.rekomendacja)}</p>
          <details><summary>Dotyczy stron: {len(g.adresy)}</summary><ul>{adresy}{reszta}</ul></details>
        </article>""")

    wiersze = "".join(
        f"<tr><td><a href=\"{escape(s.url)}\">{escape(s.tytul or s.url)}</a></td>"
        f"<td>{'produkt' if s.czy_produkt else 'strona'}</td><td>{s.status}</td>"
        f"<td>{s.czas_odpowiedzi:.2f} s</td><td class=\"{_kolor_wyniku(s.wynik)}\">{s.wynik}</td></tr>"
        for s in sorted(audyt.strony, key=lambda s: s.wynik)
    )

    return f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Audyt sklepu - {escape(audyt.adres_startowy)}</title>
<style>
  :root {{ --tlo:#f6f7f9; --karta:#fff; --tekst:#1d2330; --szary:#667085;
          --czerwony:#d92d20; --pomarancz:#dc6803; --niebieski:#2e6bd0; --zielony:#079455; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:16px/1.5 system-ui, sans-serif; background:var(--tlo); color:var(--tekst); }}
  main {{ max-width:960px; margin:0 auto; padding:32px 16px; }}
  h1 {{ margin:0 0 4px; }} .podtytul {{ color:var(--szary); margin:0 0 24px; overflow-wrap:anywhere; }}
  .podsumowanie {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin-bottom:32px; }}
  .kafel {{ background:var(--karta); border-radius:12px; padding:16px; box-shadow:0 1px 2px #0001; }}
  .kafel .liczba {{ font-size:32px; font-weight:700; }} .kafel .etykieta {{ color:var(--szary); font-size:14px; }}
  .dobry {{ color:var(--zielony); }} .sredni {{ color:var(--pomarancz); }} .slaby {{ color:var(--czerwony); }}
  .problem {{ background:var(--karta); border-radius:12px; padding:16px 20px; margin-bottom:12px;
             border-left:6px solid var(--niebieski); box-shadow:0 1px 2px #0001; }}
  .problem.krytyczny {{ border-color:var(--czerwony); }} .problem.wazny {{ border-color:var(--pomarancz); }}
  .problem h3 {{ margin:4px 0 8px; font-size:17px; }}
  .waga {{ font-size:12px; text-transform:uppercase; letter-spacing:.05em; color:var(--szary); }}
  details ul {{ margin:8px 0 0; padding-left:20px; overflow-wrap:anywhere; font-size:14px; }}
  .tabela {{ overflow-x:auto; background:var(--karta); border-radius:12px; box-shadow:0 1px 2px #0001; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  th, td {{ text-align:left; padding:8px 12px; border-bottom:1px solid #eaecf0; }}
  td:last-child {{ font-weight:700; }}
  a {{ color:var(--niebieski); }}
  footer {{ color:var(--szary); font-size:13px; margin-top:32px; }}
</style>
</head>
<body><main>
  <h1>Audyt sklepu internetowego</h1>
  <p class="podtytul">{escape(audyt.adres_startowy)} · {date.today().isoformat()}</p>

  <section class="podsumowanie">
    <div class="kafel"><div class="liczba {_kolor_wyniku(audyt.wynik)}">{audyt.wynik}/100</div><div class="etykieta">ocena ogólna</div></div>
    <div class="kafel"><div class="liczba">{len(audyt.strony)}</div><div class="etykieta">sprawdzonych stron</div></div>
    <div class="kafel"><div class="liczba">{sum(s.czy_produkt for s in audyt.strony)}</div><div class="etykieta">kart produktów</div></div>
    <div class="kafel"><div class="liczba slaby">{licznik[Waga.KRYTYCZNY]}</div><div class="etykieta">problemy krytyczne</div></div>
    <div class="kafel"><div class="liczba sredni">{licznik[Waga.WAZNY]}</div><div class="etykieta">problemy ważne</div></div>
    <div class="kafel"><div class="liczba">{licznik[Waga.DROBNY]}</div><div class="etykieta">problemy drobne</div></div>
  </section>

  <h2>Znalezione problemy</h2>
  {"".join(karty_problemow) or "<p>Nie znaleziono problemów. 🎉</p>"}

  <h2>Sprawdzone strony</h2>
  <div class="tabela"><table>
    <thead><tr><th>Strona</th><th>Typ</th><th>HTTP</th><th>Czas</th><th>Ocena</th></tr></thead>
    <tbody>{wiersze}</tbody>
  </table></div>

  <footer>Raport wygenerowany automatycznie przez narzędzie audyt-sklepu.</footer>
</main></body>
</html>
"""


def zapisz_html(audyt: Audyt, sciezka: str) -> None:
    with open(sciezka, "w", encoding="utf-8") as f:
        f.write(render_html(audyt))
