import pytest

from calcolatore.climate_data import (
    TEMPERATURA_INTERNA_DEFAULT,
    get_dati_climatici,
    get_profilo_uso,
    get_trasmittanze,
)
from calcolatore.interface_bridge import (
    InputStanza,
    a_dati_stanza,
    a_stanza_per_zonizzazione,
    converti_stanze,
)
from calcolatore.thermal_calc import calcola_carico_edificio


def test_a_dati_stanza_usa_ricambi_aria_di_default_per_uso():
    input_stanza = InputStanza(
        nome="Bagno",
        superficie=6,
        altezza=2.7,
        esposizione="N",
        stanza_angolo=False,
        superficie_finestre=1,
        uso="bagno",
    )

    dati = a_dati_stanza(input_stanza)

    assert dati.ricambi_aria_orari == get_profilo_uso("bagno").ricambi_aria_orari


def test_a_dati_stanza_rispetta_ricambi_aria_sovrascritti():
    input_stanza = InputStanza(
        nome="Bagno",
        superficie=6,
        altezza=2.7,
        esposizione="N",
        stanza_angolo=False,
        superficie_finestre=1,
        uso="bagno",
        ricambi_aria_orari=2.0,
    )

    dati = a_dati_stanza(input_stanza)

    assert dati.ricambi_aria_orari == 2.0


def test_a_dati_stanza_preserva_geometria_e_flag_disperdenti():
    input_stanza = InputStanza(
        nome="Soggiorno",
        superficie=25,
        altezza=2.7,
        esposizione="S",
        stanza_angolo=True,
        superficie_finestre=6,
        uso="soggiorno",
        ultimo_piano=True,
        piano_terra=True,
    )

    dati = a_dati_stanza(input_stanza)

    assert dati.nome == "Soggiorno"
    assert dati.superficie == 25
    assert dati.altezza == 2.7
    assert dati.superficie_finestre == 6
    assert dati.stanza_angolo is True
    assert dati.ultimo_piano is True
    assert dati.piano_terra is True


def test_a_stanza_per_zonizzazione_preserva_esposizione_e_uso():
    input_stanza = InputStanza(
        nome="Camera1",
        superficie=14,
        altezza=2.7,
        esposizione="E",
        stanza_angolo=False,
        superficie_finestre=3,
        uso="camera",
    )

    stanza_zon = a_stanza_per_zonizzazione(input_stanza)

    assert stanza_zon.nome == "Camera1"
    assert stanza_zon.esposizione == "E"
    assert stanza_zon.uso == "camera"


def test_converti_stanze_produce_liste_allineate_nello_stesso_ordine():
    stanze = [
        InputStanza("A", 10, 2.7, "N", False, 1, "camera"),
        InputStanza("B", 10, 2.7, "S", False, 1, "cucina"),
    ]

    dati_stanze, stanze_zonizzazione = converti_stanze(stanze)

    assert [d.nome for d in dati_stanze] == ["A", "B"]
    assert [s.nome for s in stanze_zonizzazione] == ["A", "B"]


def test_bridge_riproduce_i_valori_dello_script_di_esempio():
    """Stesso caso di riferimento di scripts/esempio_end_to_end.py (Milano,
    isolamento 1991-2005): il bridge deve produrre esattamente gli stessi
    carichi già verificati a mano, così un bug di wiring nell'interfaccia
    si scopre confrontando questi numeri, senza doverli ricontrollare a mano."""
    stanze_input = [
        InputStanza("Soggiorno", 25.0, 2.7, "S", False, 6.0, "soggiorno"),
        InputStanza("Cucina", 12.0, 2.7, "N", False, 2.0, "cucina"),
        InputStanza("Camera1", 14.0, 2.7, "E", False, 3.0, "camera"),
        InputStanza("Camera2", 14.0, 2.7, "E", False, 3.0, "camera"),
        InputStanza("Bagno", 6.0, 2.7, "N", False, 1.0, "bagno", ultimo_piano=True),
    ]

    dati_stanze, _ = converti_stanze(stanze_input)
    trasmittanze = get_trasmittanze("1991_2005")
    dati_clima = get_dati_climatici("Milano")

    risultati = calcola_carico_edificio(
        dati_stanze,
        trasmittanze,
        TEMPERATURA_INTERNA_DEFAULT,
        dati_clima.temperatura_esterna_progetto,
    )

    attesi_w = {
        "Soggiorno": 849,
        "Cucina": 536,
        "Camera1": 492,
        "Camera2": 492,
        "Bagno": 441,
    }
    for risultato in risultati:
        assert risultato.q_totale_w == pytest.approx(attesi_w[risultato.nome], abs=1)

    totale_w = sum(r.q_totale_w for r in risultati)
    assert totale_w == pytest.approx(2810, abs=2)
