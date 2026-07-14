"""Dati climatici e trasmittanze di default per il dimensionamento.

Tabelle statiche per zone climatiche italiane, epoche costruttive e usi
tipici degli ambienti. Valori di riferimento indicativi, pensati per una
stima preliminare — non sostituiscono i gradi-giorno ufficiali del Comune
(DPR 412/93, All. A) né un rilievo puntuale delle trasmittanze reali per un
calcolo esecutivo.
"""

from dataclasses import dataclass

from calcolatore.thermal_calc import Trasmittanze

TEMPERATURA_INTERNA_DEFAULT = 20.0  # °C, temperatura di progetto invernale standard


@dataclass(frozen=True)
class DatiClimatici:
    """Dati climatici di riferimento per una città (DPR 412/93)."""

    citta: str
    zona_climatica: str  # A-F
    gradi_giorno: int
    temperatura_esterna_progetto: float  # °C, temperatura minima di progetto invernale


# MVP: elenco semplificato di città rappresentative delle zone climatiche
# B-F (verificate contro DPR 412/93 Allegato A, luglio 2026). La zona A
# copre in Italia solo pochissimi comuni ed è omessa per l'MVP.
# Bolzano è zona E (non F, correzione rispetto a una prima stesura errata),
# coerente con Milano e Torino nella tabella ufficiale.
# Cuneo (zona F, 3012 GG) è verificata su Tuttitalia.it, che cita il DPR
# 412/93 con aggiornamenti al 31/10/2009 (coerente con la soglia GG>3000
# di zona F); temperatura di progetto -10°C da tabella UNI 5364.
CITTA_DISPONIBILI: dict[str, DatiClimatici] = {
    "Palermo": DatiClimatici("Palermo", "B", 751, 5.0),
    "Napoli": DatiClimatici("Napoli", "C", 1034, 2.0),
    "Roma": DatiClimatici("Roma", "D", 1415, 0.0),
    "Milano": DatiClimatici("Milano", "E", 2404, -5.0),
    "Torino": DatiClimatici("Torino", "E", 2617, -8.0),
    "Bolzano": DatiClimatici("Bolzano", "E", 2791, -15.0),
    "Cuneo": DatiClimatici("Cuneo", "F", 3012, -10.0),
}


@dataclass(frozen=True)
class LivelloIsolamento:
    """Trasmittanze di default per una fascia di epoca costruttiva."""

    etichetta: str
    trasmittanze: Trasmittanze


# Valori U [W/(m²K)] approssimativi e tabellati per fascia di epoca
# costruttiva, coerenti con l'evoluzione dei requisiti minimi normativi
# italiani (L.373/76, L.10/91, recepimento EPBD, NZEB). Sovrascrivibili
# manualmente dall'utente se conosce le trasmittanze reali dell'edificio.
LIVELLI_ISOLAMENTO: dict[str, LivelloIsolamento] = {
    "ante_1976": LivelloIsolamento(
        "Ante 1976 (nessun isolamento)",
        Trasmittanze(parete=1.2, copertura=1.5, pavimento=1.2, finestra=5.0),
    ),
    "1976_1990": LivelloIsolamento(
        "1976-1990 (isolamento minimo, L.373/76)",
        Trasmittanze(parete=0.9, copertura=1.0, pavimento=0.9, finestra=4.0),
    ),
    "1991_2005": LivelloIsolamento(
        "1991-2005 (L.10/91)",
        Trasmittanze(parete=0.6, copertura=0.5, pavimento=0.6, finestra=3.0),
    ),
    "2006_2015": LivelloIsolamento(
        "2006-2015 (recepimento EPBD, requisiti minimi)",
        Trasmittanze(parete=0.34, copertura=0.30, pavimento=0.33, finestra=2.2),
    ),
    "post_2015": LivelloIsolamento(
        "Post 2015 (NZEB, classe A)",
        Trasmittanze(parete=0.24, copertura=0.22, pavimento=0.26, finestra=1.4),
    ),
}


@dataclass(frozen=True)
class ProfiloUso:
    """Valori di default per ricambi d'aria e occupazione secondo l'uso della stanza."""

    etichetta: str
    ricambi_aria_orari: float  # vol/h, di riferimento UNI 10339
    occupanti_default: int


# Ricambi aria di riferimento UNI 10339 per destinazione d'uso (valori
# indicativi per ventilazione naturale/infiltrazione in ambito residenziale
# e terziario minuto; cucina e bagno più alti per l'estrazione tipica).
PROFILI_USO: dict[str, ProfiloUso] = {
    "camera": ProfiloUso("Camera da letto", ricambi_aria_orari=0.5, occupanti_default=1),
    "soggiorno": ProfiloUso("Soggiorno", ricambi_aria_orari=0.5, occupanti_default=2),
    "cucina": ProfiloUso("Cucina", ricambi_aria_orari=1.0, occupanti_default=1),
    "bagno": ProfiloUso("Bagno", ricambi_aria_orari=1.5, occupanti_default=0),
    "ufficio": ProfiloUso("Ufficio", ricambi_aria_orari=0.5, occupanti_default=1),
}


def get_dati_climatici(citta: str) -> DatiClimatici:
    """Restituisce i dati climatici di riferimento per una città disponibile."""
    try:
        return CITTA_DISPONIBILI[citta]
    except KeyError:
        raise ValueError(
            f"Città '{citta}' non disponibile. Città supportate: "
            f"{', '.join(CITTA_DISPONIBILI)}"
        ) from None


def get_trasmittanze(livello_isolamento: str) -> Trasmittanze:
    """Restituisce le trasmittanze di default per una fascia di epoca costruttiva."""
    try:
        return LIVELLI_ISOLAMENTO[livello_isolamento].trasmittanze
    except KeyError:
        raise ValueError(
            f"Livello di isolamento '{livello_isolamento}' non disponibile. "
            f"Valori supportati: {', '.join(LIVELLI_ISOLAMENTO)}"
        ) from None


def get_profilo_uso(uso: str) -> ProfiloUso:
    """Restituisce il profilo di default (ricambi aria, occupanti) per un uso stanza."""
    try:
        return PROFILI_USO[uso]
    except KeyError:
        raise ValueError(
            f"Uso '{uso}' non disponibile. Valori supportati: {', '.join(PROFILI_USO)}"
        ) from None
