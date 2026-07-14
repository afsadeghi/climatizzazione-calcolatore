"""Catalogo di riferimento di modelli di climatizzatori, con dati verificati
da schede tecniche pubbliche. Ogni voce riporta la fonte in fonte_dati.
Catalogo volutamente piccolo e curato: non esaustivo del mercato."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelloClimatizzatore:
    produttore: str
    modello: str
    tipologia: str  # "monosplit", "multisplit", "canalizzato", "cassetta"
    potenza_nominale_kw: float
    potenza_min_kw: Optional[float]
    potenza_max_kw: float
    seer: Optional[float]
    scop: Optional[float]
    num_zone_max: int
    gas_refrigerante: str
    fascia_prezzo: str  # "economico", "medio", "premium"
    fonte_dati: str


CATALOGO_INIZIALE = [
    ModelloClimatizzatore(
        produttore="Daikin",
        modello="Perfera FTXM35R",
        tipologia="monosplit",
        potenza_nominale_kw=3.4,
        potenza_min_kw=0.9,
        potenza_max_kw=4.0,
        seer=8.65,
        scop=5.10,
        num_zone_max=1,
        gas_refrigerante="R32",
        fascia_prezzo="medio",
        fonte_dati="Scheda tecnica Daikin Perfera FTXM-R; climaconvenienza.it",
    ),
    ModelloClimatizzatore(
        produttore="Daikin",
        modello="3MXM52A9 (multisplit fino a 3 zone)",
        tipologia="multisplit",
        potenza_nominale_kw=5.2,
        potenza_min_kw=0.9,
        potenza_max_kw=8.5,
        seer=9.47,
        scop=5.20,
        num_zone_max=3,
        gas_refrigerante="R32",
        fascia_prezzo="premium",
        fonte_dati="daikin.eu, Perfera Product Profile ECPIT24-008A (Italiano)",
    ),
    ModelloClimatizzatore(
        produttore="Mitsubishi Electric",
        modello="MSZ-HR35VF",
        tipologia="monosplit",
        potenza_nominale_kw=3.4,
        potenza_min_kw=0.7,
        potenza_max_kw=3.6,
        seer=6.2,
        scop=4.3,
        num_zone_max=1,
        gas_refrigerante="R32",
        fascia_prezzo="economico",
        fonte_dati="promoclima.it, scheda tecnica distributore",
    ),
    ModelloClimatizzatore(
        produttore="Daikin",
        modello="FBA71A9 canalizzabile media prevalenza",
        tipologia="canalizzato",
        potenza_nominale_kw=6.8,
        potenza_min_kw=None,  # NON VERIFICATO
        potenza_max_kw=7.5,
        seer=None,  # NON VERIFICATO: nota solo classe A++, non il valore numerico
        scop=None,  # NON VERIFICATO
        num_zone_max=1,
        gas_refrigerante="R32",
        fascia_prezzo="premium",
        fonte_dati=(
            "tavolla.com — ATTENZIONE: SEER/SCOP numerici non verificati, "
            "nota solo classe energetica A++. Da completare con scheda "
            "tecnica ufficiale Daikin serie FBA-A prima di un uso reale."
        ),
    ),
]
