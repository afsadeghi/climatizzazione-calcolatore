"""Raggruppamento delle stanze in zone termiche.

Modulo puro: nessuna dipendenza da UI né dagli altri moduli del progetto.

Criterio MVP: ogni stanza è di default una zona indipendente (controllo
separato). Se il numero di stanze supera il massimo di zone gestibili da
una centralina (default 16, tipico dei sistemi multizona commerciali), le
zone vengono accorpate progressivamente privilegiando stanze con
esposizione e/o uso simili, finché il numero di zone rientra nel limite.
"""

from dataclasses import dataclass
from itertools import combinations

MAX_ZONE_DEFAULT = 16


@dataclass(frozen=True)
class StanzaPerZonizzazione:
    """Dati minimi di una stanza necessari per il raggruppamento in zone."""

    nome: str
    esposizione: str  # es. "N", "S", "N-E"
    uso: str  # es. "camera", "soggiorno", "cucina", "bagno", "ufficio"


@dataclass(frozen=True)
class Zona:
    """Una zona termica: gruppo di stanze con controllo comune."""

    nome: str
    stanze: tuple[str, ...]  # nomi delle stanze incluse nella zona


def _similarita(
    gruppo_a: list[StanzaPerZonizzazione], gruppo_b: list[StanzaPerZonizzazione]
) -> int:
    """Punteggio di similarità tra due gruppi: +1 se condividono almeno
    un'esposizione, +1 se condividono almeno un uso."""
    esposizioni_a = {s.esposizione for s in gruppo_a}
    esposizioni_b = {s.esposizione for s in gruppo_b}
    usi_a = {s.uso for s in gruppo_a}
    usi_b = {s.uso for s in gruppo_b}

    punteggio = 0
    if esposizioni_a & esposizioni_b:
        punteggio += 1
    if usi_a & usi_b:
        punteggio += 1
    return punteggio


def _nome_zona(gruppo: list[StanzaPerZonizzazione], indice: int) -> str:
    """Genera un nome descrittivo per la zona se il gruppo condivide un
    tratto comune (uso e/o esposizione), altrimenti un nome generico."""
    esposizioni = {s.esposizione for s in gruppo}
    usi = {s.uso for s in gruppo}

    if len(usi) == 1 and len(esposizioni) == 1:
        return f"Zona {indice} ({usi.pop()}, esp. {esposizioni.pop()})"
    if len(usi) == 1:
        return f"Zona {indice} ({usi.pop()})"
    if len(esposizioni) == 1:
        return f"Zona {indice} (esp. {esposizioni.pop()})"
    return f"Zona {indice}"


def raggruppa_in_zone(
    stanze: list[StanzaPerZonizzazione], max_zone: int = MAX_ZONE_DEFAULT
) -> list[Zona]:
    """Raggruppa le stanze in zone termiche entro un numero massimo di zone.

    Finché il numero di stanze rientra in max_zone, ogni stanza resta una
    zona a sé. In caso contrario, ad ogni passo vengono accorpati i due
    gruppi più simili (stessa esposizione e/o stesso uso hanno priorità
    su gruppi senza alcun tratto in comune), finché il numero di zone
    scende a max_zone.
    """
    if max_zone < 1:
        raise ValueError("max_zone deve essere almeno 1")
    if not stanze:
        return []

    gruppi: list[list[StanzaPerZonizzazione]] = [[s] for s in stanze]

    while len(gruppi) > max_zone:
        i_migliore, j_migliore, punteggio_migliore = 0, 1, -1
        for i, j in combinations(range(len(gruppi)), 2):
            punteggio = _similarita(gruppi[i], gruppi[j])
            dimensione_candidata = len(gruppi[i]) + len(gruppi[j])
            dimensione_migliore = len(gruppi[i_migliore]) + len(gruppi[j_migliore])
            if punteggio > punteggio_migliore or (
                punteggio == punteggio_migliore and dimensione_candidata < dimensione_migliore
            ):
                i_migliore, j_migliore, punteggio_migliore = i, j, punteggio

        gruppi[i_migliore].extend(gruppi.pop(j_migliore))

    return [
        Zona(nome=_nome_zona(gruppo, indice + 1), stanze=tuple(s.nome for s in gruppo))
        for indice, gruppo in enumerate(gruppi)
    ]
