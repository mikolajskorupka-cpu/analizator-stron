"""Struktury danych używane w całym projekcie."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Waga(str, Enum):
    """Jak poważny jest problem."""

    KRYTYCZNY = "krytyczny"
    WAZNY = "ważny"
    DROBNY = "drobny"


# Ile punktów (na 100) odejmuje jeden problem danej wagi.
KARA = {Waga.KRYTYCZNY: 25, Waga.WAZNY: 10, Waga.DROBNY: 3}


@dataclass
class Problem:
    kod: str            # krótki identyfikator, np. "brak-title"
    waga: Waga
    opis: str           # co jest nie tak, po ludzku
    rekomendacja: str   # co z tym zrobić


@dataclass
class Strona:
    url: str
    status: int
    czas_odpowiedzi: float      # w sekundach
    html: str = ""
    tytul: str = ""
    czy_produkt: bool = False
    problemy: list[Problem] = field(default_factory=list)

    @property
    def wynik(self) -> int:
        """Ocena strony 0-100: startujemy od 100 i odejmujemy kary."""
        kara = sum(KARA[p.waga] for p in self.problemy)
        return max(0, 100 - kara)


@dataclass
class Audyt:
    adres_startowy: str
    strony: list[Strona] = field(default_factory=list)
    problemy_serwisu: list[Problem] = field(default_factory=list)

    @property
    def wynik(self) -> int:
        """Ocena całego sklepu: średnia ocen stron minus kary za problemy całego serwisu."""
        if not self.strony:
            return 0
        srednia = sum(s.wynik for s in self.strony) / len(self.strony)
        kara = sum(KARA[p.waga] for p in self.problemy_serwisu)
        return max(0, round(srednia - kara))
