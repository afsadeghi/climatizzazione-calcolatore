"""Interfaccia Streamlit — Calcolatore di dimensionamento climatizzazione
multizona (MVP).

Scope MVP: solo carico termico invernale, fino a 6 stanze, nessun export.
Carico estivo, portata aria, dimensionamento unità esterna ed export
CSV/PDF sono rimandati a una fase successiva (vedi avviso in fondo alla
pagina dei risultati).
"""

import streamlit as st

from calcolatore.climate_data import (
    CITTA_DISPONIBILI,
    LIVELLI_ISOLAMENTO,
    PROFILI_USO,
    TEMPERATURA_INTERNA_DEFAULT,
    get_dati_climatici,
    get_trasmittanze,
)
from calcolatore.interface_bridge import InputStanza, converti_stanze
from calcolatore.raccomandazione import DISCLAIMER as DISCLAIMER_RACCOMANDAZIONE
from calcolatore.raccomandazione import (
    Candidato,
    ZonaCarico,
    raccomanda_impianti,
)
from calcolatore.thermal_calc import calcola_carico_edificio
from calcolatore.zoning import MAX_ZONE_DEFAULT, raggruppa_in_zone

MAX_STANZE = 6

PREFERENZE = {
    "bilanciato": "Bilanciato",
    "efficienza": "Efficienza (SEER/SCOP più alti)",
    "costo": "Costo (fascia prezzo più bassa)",
}

ESPOSIZIONI = ["N", "S", "E", "O", "N-E", "N-O", "S-E", "S-O"]

TIPOLOGIE_IMPIANTO = [
    "Canalizzato",
    "Espansione diretta multi-split",
    "Idronico",
    "Misto",
]

# Valori di default: riproducono il caso di riferimento già validato in
# scripts/esempio_end_to_end.py e in test_interface_bridge.py (Milano,
# isolamento 1991-2005 -> 849 W, 536 W, 492 W, 492 W, 441 W, totale 2810 W).
STANZE_DEFAULT = [
    {
        "nome": "Soggiorno", "superficie": 25.0, "altezza": 2.7, "esposizione": "S",
        "stanza_angolo": False, "superficie_finestre": 6.0, "uso": "soggiorno",
        "ultimo_piano": False, "piano_terra": False,
    },
    {
        "nome": "Cucina", "superficie": 12.0, "altezza": 2.7, "esposizione": "N",
        "stanza_angolo": False, "superficie_finestre": 2.0, "uso": "cucina",
        "ultimo_piano": False, "piano_terra": False,
    },
    {
        "nome": "Camera1", "superficie": 14.0, "altezza": 2.7, "esposizione": "E",
        "stanza_angolo": False, "superficie_finestre": 3.0, "uso": "camera",
        "ultimo_piano": False, "piano_terra": False,
    },
    {
        "nome": "Camera2", "superficie": 14.0, "altezza": 2.7, "esposizione": "E",
        "stanza_angolo": False, "superficie_finestre": 3.0, "uso": "camera",
        "ultimo_piano": False, "piano_terra": False,
    },
    {
        "nome": "Bagno", "superficie": 6.0, "altezza": 2.7, "esposizione": "N",
        "stanza_angolo": False, "superficie_finestre": 1.0, "uso": "bagno",
        "ultimo_piano": True, "piano_terra": False,
    },
]

STANZA_VUOTA_DEFAULT = {
    "nome": "", "superficie": 12.0, "altezza": 2.7, "esposizione": "N",
    "stanza_angolo": False, "superficie_finestre": 2.0, "uso": "camera",
    "ultimo_piano": False, "piano_terra": False,
}


def _mostra_banner_avviso() -> None:
    """Banner di avviso permanente: sticky in cima alla pagina, visibile
    anche durante lo scroll, non un tooltip né un testo in fondo alla
    pagina."""
    st.markdown(
        """
        <style>
        .avviso-preliminare {
            position: sticky;
            top: 0;
            z-index: 999;
            background-color: #7a2e2e;
            color: #ffffff;
            padding: 0.6rem 1rem;
            border-radius: 0.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            border: 1px solid #a94442;
        }
        </style>
        <div class="avviso-preliminare">
        Stima preliminare, non sostituisce il calcolo esecutivo secondo normativa vigente
        </div>
        """,
        unsafe_allow_html=True,
    )


def _mostra_banner_raccomandazione() -> None:
    """Disclaimer permanente per la sezione di raccomandazione modelli,
    coerente in stile con il banner principale ma con colore distinto
    (informativo, non di avviso): sempre visibile sopra i risultati,
    non un tooltip né una nota in fondo alla pagina."""
    st.markdown(
        f"""
        <style>
        .disclaimer-raccomandazione {{
            background-color: #1f3a5f;
            color: #ffffff;
            padding: 0.6rem 1rem;
            border-radius: 0.25rem;
            margin: 0.5rem 0 1rem 0;
            border: 1px solid #2f5488;
        }}
        </style>
        <div class="disclaimer-raccomandazione">
        {DISCLAIMER_RACCOMANDAZIONE}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _mostra_candidato(candidato: Candidato) -> None:
    m = candidato.modello
    st.markdown(
        f"- **{m.produttore} {m.modello}** ({m.tipologia}, {m.potenza_nominale_kw:.1f} kW nominale, "
        f"margine {candidato.margine:.2f}×, fascia {m.fascia_prezzo})\n\n"
        f"  {candidato.motivazione}"
    )


def _mostra_raccomandazione(zone_carico: list[ZonaCarico], preferenza: str) -> None:
    st.subheader("Raccomandazione modelli")
    _mostra_banner_raccomandazione()

    risultato = raccomanda_impianti(zone_carico, preferenza=preferenza)

    for raccomandazione in risultato.per_zona:
        st.markdown(f"**{raccomandazione.zona.nome}** ({raccomandazione.zona.carico_termico_kw:.2f} kW)")
        if raccomandazione.messaggio_nessun_modello:
            st.warning(raccomandazione.messaggio_nessun_modello)
            continue
        for candidato in raccomandazione.candidati:
            _mostra_candidato(candidato)
        if raccomandazione.nota:
            st.info(raccomandazione.nota)

    alt = risultato.alternativa_multizona
    if alt is not None:
        st.markdown(f"**Alternativa multizona** (intero edificio, {alt.numero_zone} zone, {alt.carico_totale_kw:.2f} kW totali)")
        if alt.messaggio_nessun_modello:
            st.warning(alt.messaggio_nessun_modello)
        else:
            for candidato in alt.candidati:
                _mostra_candidato(candidato)


def _input_edificio() -> tuple[str, str]:
    st.subheader("Dati edificio")
    col1, col2, col3 = st.columns(3)

    citta_opzioni = list(CITTA_DISPONIBILI)
    with col1:
        citta = st.selectbox(
            "Città (zona climatica)",
            options=citta_opzioni,
            index=citta_opzioni.index("Milano"),
            format_func=lambda c: f"{c} (zona {CITTA_DISPONIBILI[c].zona_climatica})",
        )

    livello_opzioni = list(LIVELLI_ISOLAMENTO)
    with col2:
        livello = st.selectbox(
            "Livello di isolamento",
            options=livello_opzioni,
            index=livello_opzioni.index("1991_2005"),
            format_func=lambda k: LIVELLI_ISOLAMENTO[k].etichetta,
        )

    with col3:
        st.selectbox("Tipologia impianto desiderata", options=TIPOLOGIE_IMPIANTO)
        st.caption("Non influenza ancora il calcolo in questa versione MVP.")

    return citta, livello


def _input_stanza(indice: int, default: dict) -> InputStanza:
    with st.expander(f"Stanza {indice + 1}: {default['nome'] or '(nuova stanza)'}", expanded=(indice == 0)):
        nome = st.text_input("Nome stanza", value=default["nome"] or f"Stanza {indice + 1}", key=f"nome_{indice}")

        col1, col2 = st.columns(2)
        with col1:
            superficie = st.number_input(
                "Superficie (m²)", min_value=1.0, value=default["superficie"], step=0.5, key=f"superficie_{indice}"
            )
            altezza = st.number_input(
                "Altezza (m)", min_value=2.0, max_value=4.0, value=default["altezza"], step=0.1, key=f"altezza_{indice}"
            )
            esposizione = st.selectbox(
                "Esposizione", options=ESPOSIZIONI, index=ESPOSIZIONI.index(default["esposizione"]), key=f"esposizione_{indice}"
            )
            stanza_angolo = st.checkbox(
                "Stanza d'angolo (2 lati esterni distinti)", value=default["stanza_angolo"], key=f"angolo_{indice}"
            )

        with col2:
            superficie_finestre = st.number_input(
                "Superficie finestre (m²)", min_value=0.0, value=default["superficie_finestre"], step=0.5, key=f"finestre_{indice}"
            )
            uso_opzioni = list(PROFILI_USO)
            uso = st.selectbox(
                "Uso previsto",
                options=uso_opzioni,
                index=uso_opzioni.index(default["uso"]),
                format_func=lambda k: PROFILI_USO[k].etichetta,
                key=f"uso_{indice}",
            )
            ultimo_piano = st.checkbox(
                "Ultimo piano (soffitto disperdente verso l'esterno)", value=default["ultimo_piano"], key=f"ultimo_{indice}"
            )
            piano_terra = st.checkbox(
                "Piano terra (pavimento disperdente)", value=default["piano_terra"], key=f"terra_{indice}"
            )

    return InputStanza(
        nome=nome,
        superficie=superficie,
        altezza=altezza,
        esposizione=esposizione,
        stanza_angolo=stanza_angolo,
        superficie_finestre=superficie_finestre,
        uso=uso,
        ultimo_piano=ultimo_piano,
        piano_terra=piano_terra,
    )


def _input_stanze() -> list[InputStanza]:
    st.subheader("Stanze")
    n_stanze = st.number_input(
        "Numero di stanze (max 6)", min_value=1, max_value=MAX_STANZE, value=len(STANZE_DEFAULT)
    )

    stanze = []
    for i in range(int(n_stanze)):
        default = STANZE_DEFAULT[i] if i < len(STANZE_DEFAULT) else STANZA_VUOTA_DEFAULT
        stanze.append(_input_stanza(i, default))
    return stanze


def main() -> None:
    st.set_page_config(page_title="Calcolatore Climatizzazione Multizona", layout="wide")
    _mostra_banner_avviso()

    st.title("Calcolatore di dimensionamento climatizzazione multizona")
    st.caption(
        "MVP: solo carico termico invernale, fino a 6 stanze, nessun export. "
        "Supporto alla fase di offerta tecnica, non un calcolo esecutivo."
    )

    citta, livello = _input_edificio()
    max_zone = st.number_input(
        "Numero massimo di zone per centralina", min_value=1, max_value=32, value=MAX_ZONE_DEFAULT
    )

    stanze_input = _input_stanze()

    dati_clima = get_dati_climatici(citta)
    trasmittanze = get_trasmittanze(livello)
    dati_stanze, stanze_zonizzazione = converti_stanze(stanze_input)

    risultati = calcola_carico_edificio(
        dati_stanze,
        trasmittanze,
        TEMPERATURA_INTERNA_DEFAULT,
        dati_clima.temperatura_esterna_progetto,
    )

    st.subheader("Carico termico invernale")
    delta_t = TEMPERATURA_INTERNA_DEFAULT - dati_clima.temperatura_esterna_progetto
    st.caption(
        f"Città: {dati_clima.citta} (zona {dati_clima.zona_climatica}, {dati_clima.gradi_giorno} GG) — "
        f"temperatura interna {TEMPERATURA_INTERNA_DEFAULT:.0f}°C, "
        f"temperatura esterna di progetto {dati_clima.temperatura_esterna_progetto:.0f}°C "
        f"(ΔT = {delta_t:.1f} K)"
    )

    righe = [
        {
            "Stanza": r.nome,
            "Trasmissione (W)": round(r.q_trasmissione_w),
            "Ventilazione (W)": round(r.q_ventilazione_w),
            "Totale (W)": round(r.q_totale_w),
            "Totale (kW)": round(r.q_totale_kw, 2),
        }
        for r in risultati
    ]
    st.table(righe)

    totale_w = sum(r.q_totale_w for r in risultati)
    st.metric("Totale edificio", f"{totale_w / 1000:.2f} kW", help=f"{totale_w:.0f} W")

    st.subheader("Zonizzazione consigliata")
    zone = raggruppa_in_zone(stanze_zonizzazione, max_zone=int(max_zone))
    for zona in zone:
        st.write(f"**{zona.nome}**: {', '.join(zona.stanze)}")

    carico_per_stanza_kw = {r.nome: r.q_totale_kw for r in risultati}
    zone_carico = [
        ZonaCarico(nome=zona.nome, carico_termico_kw=sum(carico_per_stanza_kw[nome] for nome in zona.stanze))
        for zona in zone
    ]
    preferenza_opzioni = list(PREFERENZE)
    preferenza = st.selectbox(
        "Preferenza raccomandazione",
        options=preferenza_opzioni,
        index=preferenza_opzioni.index("bilanciato"),
        format_func=lambda k: PREFERENZE[k],
    )
    _mostra_raccomandazione(zone_carico, preferenza)

    st.info(
        "Non ancora disponibili in questa versione, previsti per una fase successiva: "
        "carico estivo, portata aria consigliata per zona, dimensionamento unità "
        "esterna, esportazione CSV/PDF, più di 6 stanze, salvataggio progetti."
    )


if __name__ == "__main__":
    main()
