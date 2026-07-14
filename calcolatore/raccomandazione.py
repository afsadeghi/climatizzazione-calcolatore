"""Raccomandazione di modelli di climatizzatori per zona, a partire dal
carico termico calcolato da thermal_calc.py e dalle zone di zoning.py.

Modulo puro: nessuna dipendenza da UI. Usa il catalogo statico di
catalogo.py così com'è — non lo estende né lo completa con dati "a
memoria": un carico non coperto dal catalogo attuale viene segnalato
esplicitamente, non forzato su un modello inadeguato.

Nota di design sui campi mancanti (None) nel catalogo: il catalogo
distingue due casi diversi, trattati diversamente qui.
- SEER/SCOP mancanti (FBA71A9): il modello resta candidato per capacità,
  ma è escluso dall'ordinamento per "efficienza" e riceve sempre un
  flag esplicito, per richiesta della specifica.
- potenza_min_kw mancante (FBA71A9): la specifica non lo tratta
  esplicitamente. Qui si è scelto, per coerenza con lo stesso principio,
  di NON escludere il modello dal matching di capacità (non possiamo
  affermare che NON copra un carico basso, ma non possiamo nemmeno
  affermarlo con certezza), aggiungendo però un flag esplicito che lo
  segnala come dato non verificato. Questo significa che, con il
  catalogo attuale, un carico molto basso non fa mai scattare il caso
  "nessun modello adeguato" da solo (FBA71A9 resta sempre candidato per
  capacità in quel caso, seppure fortemente sovradimensionato e
  flaggato): il caso "nessun modello adeguato" si verifica in pratica
  solo per carichi troppo ALTI per l'intero catalogo.
"""

from dataclasses import dataclass

from calcolatore.catalogo import CATALOGO_INIZIALE, ModelloClimatizzatore

MARGINE_MIN = 1.10
MARGINE_MAX = 1.30

PREFERENZE_VALIDE = ("efficienza", "costo", "bilanciato")

DISCLAIMER = (
    "Raccomandazione basata su un catalogo limitato di riferimento, non "
    "esaustivo del mercato. La scelta finale dell'impianto spetta a un "
    "installatore qualificato, che valuterà anche vincoli di posizionamento, "
    "alimentazione elettrica e normative locali."
)

FLAG_EFFICIENZA_MANCANTE = "dati di efficienza non disponibili — verificare scheda tecnica"
FLAG_POTENZA_MIN_MANCANTE = "potenza minima di modulazione non verificata — verificare scheda tecnica"

_ORDINE_PREZZO = {"economico": 3, "medio": 2, "premium": 1}


@dataclass(frozen=True)
class ZonaCarico:
    """Una zona termica con il relativo carico invernale totale."""

    nome: str
    carico_termico_kw: float


@dataclass(frozen=True)
class Candidato:
    """Un modello candidato per una zona (o per l'intero edificio), con motivazione."""

    modello: ModelloClimatizzatore
    margine: float  # potenza_nominale_kw / carico_kw, es. 1.15 = +15%
    dentro_margine_ideale: bool  # True se margine in [MARGINE_MIN, MARGINE_MAX]
    flags: tuple[str, ...]
    motivazione: str


@dataclass(frozen=True)
class RaccomandazioneZona:
    """Risultato della raccomandazione per una singola zona."""

    zona: ZonaCarico
    candidati: list[Candidato]  # 0-3, già ordinati secondo la preferenza
    messaggio_nessun_modello: str | None


@dataclass(frozen=True)
class AlternativaMultizona:
    """Alternativa: un singolo modello multisplit per l'intero edificio,
    invece di più unità monozona separate. Proposta solo se ci sono più
    zone; la scelta tra le due opzioni spetta all'installatore."""

    candidati: list[Candidato]
    carico_totale_kw: float
    numero_zone: int
    messaggio_nessun_modello: str | None


@dataclass(frozen=True)
class RisultatoRaccomandazione:
    """Risultato completo: raccomandazione per zona più, se pertinente,
    l'alternativa multizona."""

    per_zona: list[RaccomandazioneZona]
    alternativa_multizona: AlternativaMultizona | None
    disclaimer: str = DISCLAIMER


def _punteggio_efficienza(modello: ModelloClimatizzatore) -> float | None:
    if modello.seer is None or modello.scop is None:
        return None
    return modello.seer + modello.scop


def _e_candidato_per_capacita(modello: ModelloClimatizzatore, carico_kw: float) -> bool:
    """Un modello è candidato per capacità se il carico rientra nel suo
    range operativo [potenza_min_kw, potenza_max_kw]. Se potenza_min_kw
    non è verificato (None), il vincolo inferiore non viene applicato
    (vedi nota di modulo)."""
    if carico_kw > modello.potenza_max_kw:
        return False
    if modello.potenza_min_kw is not None and carico_kw < modello.potenza_min_kw:
        return False
    return True


def _candidato_da_modello(modello: ModelloClimatizzatore, carico_kw: float) -> Candidato:
    margine = modello.potenza_nominale_kw / carico_kw
    dentro_margine_ideale = MARGINE_MIN <= margine <= MARGINE_MAX
    percentuale = (margine - 1) * 100

    flags: list[str] = []
    if modello.seer is None or modello.scop is None:
        flags.append(FLAG_EFFICIENZA_MANCANTE)
    if modello.potenza_min_kw is None:
        flags.append(FLAG_POTENZA_MIN_MANCANTE)

    if dentro_margine_ideale:
        motivazione = (
            f"Copre il carico con margine di sovradimensionamento del "
            f"{percentuale:.0f}% (in linea con la prassi 10-30%)."
        )
    elif margine < MARGINE_MIN:
        motivazione = (
            f"Copre il carico ma con margine di sovradimensionamento ridotto "
            f"({percentuale:.0f}%, sotto il 10% consigliato) — verificare in sopralluogo."
        )
    else:
        motivazione = (
            f"Copre il carico ma con margine di sovradimensionamento elevato "
            f"({percentuale:.0f}%, sopra il 30% consigliato) — rischio di cicli brevi."
        )

    if flags:
        motivazione += " " + " ".join(f"[{flag}]" for flag in flags)

    return Candidato(
        modello=modello,
        margine=margine,
        dentro_margine_ideale=dentro_margine_ideale,
        flags=tuple(flags),
        motivazione=motivazione,
    )


def _normalizza(valore: float, minimo: float, massimo: float) -> float:
    if massimo == minimo:
        return 1.0
    return (valore - minimo) / (massimo - minimo)


def _ordina_per_preferenza(candidati: list[Candidato], preferenza: str) -> list[Candidato]:
    """Ordina i candidati secondo la preferenza utente.

    - "efficienza": SEER+SCOP decrescenti; i modelli senza dati di
      efficienza sono esclusi da questo ordinamento (vanno in coda,
      nell'ordine originale) ma restano nella lista.
    - "costo": fascia_prezzo crescente (economico -> medio -> premium).
    - "bilanciato": media semplice (pesi uguali) tra efficienza e prezzo,
      entrambi normalizzati in [0, 1] sull'insieme dei candidati. I
      modelli senza dati di efficienza ricevono 0 per quella componente
      (non favoriti né esclusi dal punteggio complessivo). Questa è una
      scelta di design non specificata univocamente a monte: "media
      pesata semplice" è interpretata come media aritmetica 50/50.
    """
    if preferenza not in PREFERENZE_VALIDE:
        raise ValueError(
            f"Preferenza '{preferenza}' non riconosciuta. Valori validi: {', '.join(PREFERENZE_VALIDE)}"
        )

    if not candidati:
        return []

    if preferenza == "efficienza":
        con_efficienza = [c for c in candidati if _punteggio_efficienza(c.modello) is not None]
        senza_efficienza = [c for c in candidati if _punteggio_efficienza(c.modello) is None]
        con_efficienza.sort(key=lambda c: _punteggio_efficienza(c.modello), reverse=True)
        return con_efficienza + senza_efficienza

    if preferenza == "costo":
        return sorted(candidati, key=lambda c: _ORDINE_PREZZO.get(c.modello.fascia_prezzo, 0), reverse=True)

    # bilanciato
    punteggi_efficienza = [
        _punteggio_efficienza(c.modello) for c in candidati if _punteggio_efficienza(c.modello) is not None
    ]
    eff_min = min(punteggi_efficienza) if punteggi_efficienza else 0.0
    eff_max = max(punteggi_efficienza) if punteggi_efficienza else 1.0
    prezzi = [_ORDINE_PREZZO.get(c.modello.fascia_prezzo, 0) for c in candidati]
    prezzo_min, prezzo_max = min(prezzi), max(prezzi)

    def punteggio_bilanciato(c: Candidato) -> float:
        eff = _punteggio_efficienza(c.modello)
        eff_norm = 0.0 if eff is None else _normalizza(eff, eff_min, eff_max)
        prezzo_norm = _normalizza(_ORDINE_PREZZO.get(c.modello.fascia_prezzo, 0), prezzo_min, prezzo_max)
        return 0.5 * eff_norm + 0.5 * prezzo_norm

    return sorted(candidati, key=punteggio_bilanciato, reverse=True)


def _messaggio_nessun_modello(carico_kw: float, modelli: list[ModelloClimatizzatore]) -> str:
    potenze_min_note = [m.potenza_min_kw for m in modelli if m.potenza_min_kw is not None]
    potenze_max = [m.potenza_max_kw for m in modelli]
    range_min = min(potenze_min_note) if potenze_min_note else min(potenze_max)
    range_max = max(potenze_max)
    return (
        f"Nessun modello nel catalogo attuale copre questo carico — "
        f"carico zona: {carico_kw:.2f} kW, "
        f"range disponibile nel catalogo: {range_min:.2f}-{range_max:.2f} kW"
    )


def raccomanda_per_zona(
    zona: ZonaCarico,
    preferenza: str = "bilanciato",
    catalogo: list[ModelloClimatizzatore] | None = None,
) -> RaccomandazioneZona:
    """Raccomanda 1-3 modelli monozona (num_zone_max == 1) per una zona."""
    catalogo = catalogo if catalogo is not None else CATALOGO_INIZIALE
    modelli_monozona = [m for m in catalogo if m.num_zone_max == 1]

    idonei = [m for m in modelli_monozona if _e_candidato_per_capacita(m, zona.carico_termico_kw)]

    if not idonei:
        return RaccomandazioneZona(
            zona=zona,
            candidati=[],
            messaggio_nessun_modello=_messaggio_nessun_modello(zona.carico_termico_kw, modelli_monozona),
        )

    candidati = [_candidato_da_modello(m, zona.carico_termico_kw) for m in idonei]
    candidati_ordinati = _ordina_per_preferenza(candidati, preferenza)[:3]
    return RaccomandazioneZona(zona=zona, candidati=candidati_ordinati, messaggio_nessun_modello=None)


def _alternativa_multizona(
    zone: list[ZonaCarico],
    preferenza: str,
    catalogo: list[ModelloClimatizzatore],
) -> AlternativaMultizona | None:
    """Propone un'alternativa multisplit per l'intero edificio quando ci
    sono più zone. Restituisce None se c'è una sola zona (l'alternativa
    non ha senso: un multisplit serve a coprire più zone con un'unica
    unità esterna)."""
    if len(zone) <= 1:
        return None

    carico_totale = sum(z.carico_termico_kw for z in zone)
    modelli_multizona = [m for m in catalogo if m.num_zone_max >= len(zone)]

    idonei = [m for m in modelli_multizona if _e_candidato_per_capacita(m, carico_totale)]

    if not idonei:
        return AlternativaMultizona(
            candidati=[],
            carico_totale_kw=carico_totale,
            numero_zone=len(zone),
            messaggio_nessun_modello=_messaggio_nessun_modello(carico_totale, modelli_multizona)
            if modelli_multizona
            else (
                f"Nessun modello multisplit nel catalogo attuale supporta {len(zone)} zone — "
                f"carico totale: {carico_totale:.2f} kW"
            ),
        )

    candidati = [_candidato_da_modello(m, carico_totale) for m in idonei]
    candidati_ordinati = _ordina_per_preferenza(candidati, preferenza)[:3]
    return AlternativaMultizona(
        candidati=candidati_ordinati,
        carico_totale_kw=carico_totale,
        numero_zone=len(zone),
        messaggio_nessun_modello=None,
    )


def raccomanda_impianti(
    zone: list[ZonaCarico],
    preferenza: str = "bilanciato",
    catalogo: list[ModelloClimatizzatore] | None = None,
) -> RisultatoRaccomandazione:
    """Raccomanda modelli per ciascuna zona e, se ci sono più zone,
    un'alternativa multisplit per l'intero edificio."""
    if preferenza not in PREFERENZE_VALIDE:
        raise ValueError(
            f"Preferenza '{preferenza}' non riconosciuta. Valori validi: {', '.join(PREFERENZE_VALIDE)}"
        )
    catalogo = catalogo if catalogo is not None else CATALOGO_INIZIALE

    per_zona = [raccomanda_per_zona(z, preferenza, catalogo) for z in zone]
    alternativa = _alternativa_multizona(zone, preferenza, catalogo)

    return RisultatoRaccomandazione(per_zona=per_zona, alternativa_multizona=alternativa)
