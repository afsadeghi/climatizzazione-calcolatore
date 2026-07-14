#!/usr/bin/env python3
"""Script di integrazione end-to-end per raccomandazione.py (non un test
formale).

Riusa l'identico caso di riferimento di scripts/esempio_end_to_end.py (5
stanze a Milano, isolamento 1991-2005, zonizzate in 3 zone con
max_zone=3) e ci applica il matching con il catalogo di catalogo.py, per
vedere l'output su carta prima di costruire l'interfaccia sopra.

Uso: python3 scripts/esempio_raccomandazione.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calcolatore.climate_data import (  # noqa: E402
    TEMPERATURA_INTERNA_DEFAULT,
    get_dati_climatici,
    get_trasmittanze,
)
from calcolatore.interface_bridge import InputStanza, converti_stanze  # noqa: E402
from calcolatore.raccomandazione import (  # noqa: E402
    Candidato,
    ZonaCarico,
    raccomanda_impianti,
)
from calcolatore.thermal_calc import calcola_carico_edificio  # noqa: E402
from calcolatore.zoning import raggruppa_in_zone  # noqa: E402

CITTA = "Milano"
LIVELLO_ISOLAMENTO = "1991_2005"
MAX_ZONE = 3
PREFERENZA = "bilanciato"

# Stesso identico caso di riferimento di scripts/esempio_end_to_end.py.
STANZE_ESEMPIO = [
    ("Soggiorno", 25.0, 2.7, "S", 6.0, "soggiorno", False, False, False),
    ("Cucina", 12.0, 2.7, "N", 2.0, "cucina", False, False, False),
    ("Camera1", 14.0, 2.7, "E", 3.0, "camera", False, False, False),
    ("Camera2", 14.0, 2.7, "E", 3.0, "camera", False, False, False),
    ("Bagno", 6.0, 2.7, "N", 1.0, "bagno", False, True, False),
]


def _stampa_candidato(candidato: Candidato) -> None:
    m = candidato.modello
    print(
        f"    - {m.produttore} {m.modello} ({m.tipologia}, {m.potenza_nominale_kw:.1f} kW nominale, "
        f"margine {candidato.margine:.2f}x, fascia {m.fascia_prezzo})"
    )
    print(f"      {candidato.motivazione}")


def main() -> None:
    dati_clima = get_dati_climatici(CITTA)
    trasmittanze = get_trasmittanze(LIVELLO_ISOLAMENTO)

    stanze_input = [
        InputStanza(nome, superficie, altezza, esposizione, angolo, finestre, uso, ultimo, terra)
        for nome, superficie, altezza, esposizione, finestre, uso, angolo, ultimo, terra in STANZE_ESEMPIO
    ]
    dati_stanze, stanze_zonizzazione = converti_stanze(stanze_input)

    risultati_stanze = calcola_carico_edificio(
        dati_stanze, trasmittanze, TEMPERATURA_INTERNA_DEFAULT, dati_clima.temperatura_esterna_progetto
    )
    carico_per_stanza_kw = {r.nome: r.q_totale_kw for r in risultati_stanze}

    zone_zoning = raggruppa_in_zone(stanze_zonizzazione, max_zone=MAX_ZONE)
    zone_carico = [
        ZonaCarico(
            nome=zona.nome,
            carico_termico_kw=sum(carico_per_stanza_kw[nome] for nome in zona.stanze),
        )
        for zona in zone_zoning
    ]

    print(f"=== Zone di carico (preferenza: {PREFERENZA}) ===")
    for zona in zone_carico:
        print(f"{zona.nome}: {zona.carico_termico_kw:.3f} kW")
    print()

    risultato = raccomanda_impianti(zone_carico, preferenza=PREFERENZA)

    print("=== Raccomandazione per zona ===")
    for raccomandazione in risultato.per_zona:
        print(f"\n{raccomandazione.zona.nome} ({raccomandazione.zona.carico_termico_kw:.3f} kW):")
        if raccomandazione.messaggio_nessun_modello:
            print(f"  {raccomandazione.messaggio_nessun_modello}")
            continue
        for candidato in raccomandazione.candidati:
            _stampa_candidato(candidato)

    print("\n=== Alternativa multizona (intero edificio) ===")
    alt = risultato.alternativa_multizona
    if alt is None:
        print("  Non applicabile (una sola zona).")
    elif alt.messaggio_nessun_modello:
        print(f"  {alt.messaggio_nessun_modello}")
    else:
        print(f"  Carico totale: {alt.carico_totale_kw:.3f} kW su {alt.numero_zone} zone")
        for candidato in alt.candidati:
            _stampa_candidato(candidato)

    print(f"\n{risultato.disclaimer}")


if __name__ == "__main__":
    main()
