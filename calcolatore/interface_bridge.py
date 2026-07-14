"""Ponte tra i dati raccolti in un form (UI) e i tipi attesi da
thermal_calc.py e zoning.py.

Modulo puro: nessuna dipendenza da Streamlit o da altra libreria UI.
Isola la logica di conversione così che resti leggibile e testabile
quanto gli altri moduli, invece di essere sparsa nel codice dell'app.
"""

from dataclasses import dataclass

from calcolatore.climate_data import get_profilo_uso
from calcolatore.thermal_calc import DatiStanza
from calcolatore.zoning import StanzaPerZonizzazione


@dataclass(frozen=True)
class InputStanza:
    """Dati di una stanza così come raccolti dal form UI.

    Riunisce in un unico tipo i campi necessari sia al calcolo del
    carico termico (thermal_calc.py) sia alla zonizzazione (zoning.py),
    che nei rispettivi moduli sono rappresentati da due dataclass
    distinte e volutamente disaccoppiate.
    """

    nome: str
    superficie: float
    altezza: float
    esposizione: str
    stanza_angolo: bool
    superficie_finestre: float
    uso: str
    ultimo_piano: bool = False
    piano_terra: bool = False
    ricambi_aria_orari: float | None = None  # None = usa il default per uso


def a_dati_stanza(input_stanza: InputStanza) -> DatiStanza:
    """Converte un InputStanza nel tipo DatiStanza atteso da thermal_calc.py."""
    ricambi_aria_orari = input_stanza.ricambi_aria_orari
    if ricambi_aria_orari is None:
        ricambi_aria_orari = get_profilo_uso(input_stanza.uso).ricambi_aria_orari

    return DatiStanza(
        nome=input_stanza.nome,
        superficie=input_stanza.superficie,
        altezza=input_stanza.altezza,
        superficie_finestre=input_stanza.superficie_finestre,
        stanza_angolo=input_stanza.stanza_angolo,
        ricambi_aria_orari=ricambi_aria_orari,
        ultimo_piano=input_stanza.ultimo_piano,
        piano_terra=input_stanza.piano_terra,
    )


def a_stanza_per_zonizzazione(input_stanza: InputStanza) -> StanzaPerZonizzazione:
    """Converte un InputStanza nel tipo StanzaPerZonizzazione atteso da zoning.py."""
    return StanzaPerZonizzazione(
        nome=input_stanza.nome,
        esposizione=input_stanza.esposizione,
        uso=input_stanza.uso,
    )


def converti_stanze(
    stanze: list[InputStanza],
) -> tuple[list[DatiStanza], list[StanzaPerZonizzazione]]:
    """Converte una lista di InputStanza nelle due liste tipizzate attese
    rispettivamente da thermal_calc.py e zoning.py, nello stesso ordine."""
    dati_stanze = [a_dati_stanza(s) for s in stanze]
    stanze_zonizzazione = [a_stanza_per_zonizzazione(s) for s in stanze]
    return dati_stanze, stanze_zonizzazione
