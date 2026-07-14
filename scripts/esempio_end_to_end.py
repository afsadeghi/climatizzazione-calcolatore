#!/usr/bin/env python3
"""Script di integrazione end-to-end (non un test formale).

Prende 5 stanze di esempio, calcola il carico termico invernale con
thermal_calc.py usando i dati climatici di climate_data.py, e le
zonizza con zoning.py. Serve a verificare a occhio che i tre moduli si
incastrino correttamente prima di costruire l'interfaccia.

Uso: python3 scripts/esempio_end_to_end.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calcolatore.climate_data import (  # noqa: E402
    TEMPERATURA_INTERNA_DEFAULT,
    LIVELLI_ISOLAMENTO,
    get_dati_climatici,
    get_profilo_uso,
    get_trasmittanze,
)
from calcolatore.thermal_calc import DatiStanza, calcola_carico_edificio  # noqa: E402
from calcolatore.zoning import StanzaPerZonizzazione, raggruppa_in_zone  # noqa: E402

# --- Dati edificio -----------------------------------------------------

CITTA = "Milano"
LIVELLO_ISOLAMENTO = "1991_2005"
MAX_ZONE = 3  # forzato basso per far vedere l'accorpamento con solo 5 stanze

# --- Stanze di esempio ---------------------------------------------------
# (nome, superficie m², altezza m, esposizione, superficie finestre m², uso,
#  stanza_angolo, ultimo_piano, piano_terra)
STANZE_ESEMPIO = [
    ("Soggiorno", 25.0, 2.7, "S", 6.0, "soggiorno", False, False, False),
    ("Cucina", 12.0, 2.7, "N", 2.0, "cucina", False, False, False),
    ("Camera1", 14.0, 2.7, "E", 3.0, "camera", False, False, False),
    ("Camera2", 14.0, 2.7, "E", 3.0, "camera", False, False, False),
    ("Bagno", 6.0, 2.7, "N", 1.0, "bagno", False, True, False),
]


def main() -> None:
    dati_clima = get_dati_climatici(CITTA)
    trasmittanze = get_trasmittanze(LIVELLO_ISOLAMENTO)
    delta_t = TEMPERATURA_INTERNA_DEFAULT - dati_clima.temperatura_esterna_progetto

    print("=== Dati edificio ===")
    print(f"Città: {dati_clima.citta} (zona climatica {dati_clima.zona_climatica}, "
          f"{dati_clima.gradi_giorno} GG)")
    print(f"Temperatura interna di progetto: {TEMPERATURA_INTERNA_DEFAULT:.1f}°C")
    print(f"Temperatura esterna di progetto: {dati_clima.temperatura_esterna_progetto:.1f}°C "
          f"(ΔT = {delta_t:.1f} K)")
    print(f"Livello di isolamento: {LIVELLI_ISOLAMENTO[LIVELLO_ISOLAMENTO].etichetta}")
    print()

    stanze_calc = []
    for nome, superficie, altezza, _esposizione, superficie_finestre, uso, angolo, ultimo, terra in STANZE_ESEMPIO:
        profilo = get_profilo_uso(uso)
        stanze_calc.append(
            DatiStanza(
                nome=nome,
                superficie=superficie,
                altezza=altezza,
                superficie_finestre=superficie_finestre,
                stanza_angolo=angolo,
                ricambi_aria_orari=profilo.ricambi_aria_orari,
                ultimo_piano=ultimo,
                piano_terra=terra,
            )
        )

    risultati = calcola_carico_edificio(
        stanze_calc, trasmittanze, TEMPERATURA_INTERNA_DEFAULT, dati_clima.temperatura_esterna_progetto
    )

    print("=== Carico termico invernale per stanza ===")
    intestazione = f"{'Stanza':<12}{'Trasmissione':>14}{'Ventilazione':>14}{'Totale':>12}{'':>10}"
    print(intestazione)
    print("-" * len(intestazione))
    totale_edificio_w = 0.0
    for risultato in risultati:
        totale_edificio_w += risultato.q_totale_w
        print(
            f"{risultato.nome:<12}{risultato.q_trasmissione_w:>11.0f} W"
            f"{risultato.q_ventilazione_w:>11.0f} W"
            f"{risultato.q_totale_w:>9.0f} W"
            f"{risultato.q_totale_kw:>8.2f} kW"
        )
    print("-" * len(intestazione))
    print(f"{'TOTALE EDIFICIO':<40}{totale_edificio_w:>9.0f} W{totale_edificio_w / 1000:>8.2f} kW")
    print()

    stanze_zonizzazione = [
        StanzaPerZonizzazione(nome=nome, esposizione=esposizione, uso=uso)
        for nome, _s, _a, esposizione, _sf, uso, *_resto in STANZE_ESEMPIO
    ]
    zone = raggruppa_in_zone(stanze_zonizzazione, max_zone=MAX_ZONE)

    print(f"=== Zonizzazione (max {MAX_ZONE} zone) ===")
    for zona in zone:
        print(f"{zona.nome}: {', '.join(zona.stanze)}")


if __name__ == "__main__":
    main()
