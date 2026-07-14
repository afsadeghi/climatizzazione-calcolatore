"""Calcolo del carico termico invernale per singola stanza.

Metodo semplificato ispirato a EN 12831 / UNI/TS 11300:

    Q = Q_trasmissione + Q_ventilazione

Modulo puro: nessuna dipendenza da UI o da altri moduli del progetto.
Tutte le grandezze di input/output sono tipizzate con dataclass.
"""

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class Trasmittanze:
    """Trasmittanze termiche U [W/(m²K)] degli elementi disperdenti."""

    parete: float
    copertura: float
    pavimento: float
    finestra: float


@dataclass(frozen=True)
class DatiStanza:
    """Dati di input per una singola stanza."""

    nome: str
    superficie: float  # m²
    altezza: float  # m
    superficie_finestre: float = 0.0  # m², superficie vetrata totale
    stanza_angolo: bool = False  # True se la stanza ha 2 lati esterni distinti (es. N e E)
    ricambi_aria_orari: float = 0.5  # vol/h (default residenziale UNI 10339)
    ultimo_piano: bool = False  # True se soffitto disperdente verso l'esterno
    piano_terra: bool = False  # True se pavimento disperdente verso terreno/locale non riscaldato
    fattore_riduzione_pavimento: float = 0.5  # coefficiente b semplificato per pavimento contro terra


@dataclass(frozen=True)
class RisultatoStanza:
    """Risultato del calcolo del carico termico per una singola stanza."""

    nome: str
    q_trasmissione_w: float
    q_ventilazione_w: float
    q_totale_w: float

    @property
    def q_totale_kw(self) -> float:
        return self.q_totale_w / 1000


# NOTA - bias noto dell'approssimazione a pianta quadrata: a parità di
# superficie, una stanza rettangolare allungata (es. 4m x 5m) ha un
# perimetro maggiore di una stanza quadrata equivalente (sqrt(20) x sqrt(20)),
# quindi più parete realmente disperdente di quella stimata qui. L'errore
# cresce con il rapporto di allungamento della stanza ed è quindi una
# sottostima sistematica, non casuale: da tenere presente nell'uso come
# stima preliminare, non sostitutiva di un rilievo geometrico puntuale.
def superficie_parete_esterna_lorda(dati: DatiStanza) -> float:
    """Stima la superficie lorda di parete esterna disperdente.

    Semplificazione per dimensionamento preliminare: la stanza è assimilata
    a una pianta quadrata di lato sqrt(superficie). Una singola esposizione
    (anche composta, es. "N-E") vale 1 solo lato esterno; solo una stanza
    d'angolo (stanza_angolo=True), con due esposizioni distinte (es. "N" e
    "E"), ne vale 2.
    """
    lato = sqrt(dati.superficie)
    num_lati_esterni = 2 if dati.stanza_angolo else 1
    return lato * dati.altezza * num_lati_esterni


def calcola_q_trasmissione(
    dati: DatiStanza, trasmittanze: Trasmittanze, delta_t: float
) -> float:
    """Potenza dispersa per trasmissione [W] = Σ (U_i × A_i × ΔT)."""
    parete_lorda = superficie_parete_esterna_lorda(dati)
    parete_netta = max(parete_lorda - dati.superficie_finestre, 0.0)

    q_parete = trasmittanze.parete * parete_netta * delta_t
    q_finestre = trasmittanze.finestra * dati.superficie_finestre * delta_t

    q_copertura = 0.0
    if dati.ultimo_piano:
        q_copertura = trasmittanze.copertura * dati.superficie * delta_t

    q_pavimento = 0.0
    if dati.piano_terra:
        q_pavimento = (
            trasmittanze.pavimento
            * dati.superficie
            * delta_t
            * dati.fattore_riduzione_pavimento
        )

    return q_parete + q_finestre + q_copertura + q_pavimento


def calcola_q_ventilazione(dati: DatiStanza, delta_t: float) -> float:
    """Potenza dispersa per ventilazione [W] = 0.34 × n × V × ΔT.

    0.34 Wh/(m³K) è la capacità termica volumica dell'aria.
    """
    volume = dati.superficie * dati.altezza
    return 0.34 * dati.ricambi_aria_orari * volume * delta_t


def calcola_carico_stanza(
    dati: DatiStanza,
    trasmittanze: Trasmittanze,
    temperatura_interna: float,
    temperatura_esterna: float,
) -> RisultatoStanza:
    """Calcola il carico termico invernale totale per una stanza."""
    delta_t = temperatura_interna - temperatura_esterna
    if delta_t < 0:
        raise ValueError(
            "La temperatura interna di progetto deve essere maggiore o "
            "uguale alla temperatura esterna di progetto"
        )

    q_trasmissione = calcola_q_trasmissione(dati, trasmittanze, delta_t)
    q_ventilazione = calcola_q_ventilazione(dati, delta_t)

    return RisultatoStanza(
        nome=dati.nome,
        q_trasmissione_w=q_trasmissione,
        q_ventilazione_w=q_ventilazione,
        q_totale_w=q_trasmissione + q_ventilazione,
    )


def calcola_carico_edificio(
    stanze: list[DatiStanza],
    trasmittanze: Trasmittanze,
    temperatura_interna: float,
    temperatura_esterna: float,
) -> list[RisultatoStanza]:
    """Calcola il carico termico invernale per un elenco di stanze."""
    return [
        calcola_carico_stanza(dati, trasmittanze, temperatura_interna, temperatura_esterna)
        for dati in stanze
    ]
