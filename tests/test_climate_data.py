import pytest

from calcolatore.climate_data import (
    CITTA_DISPONIBILI,
    LIVELLI_ISOLAMENTO,
    PROFILI_USO,
    get_dati_climatici,
    get_profilo_uso,
    get_trasmittanze,
)


def test_get_dati_climatici_citta_valida():
    dati = get_dati_climatici("Milano")
    assert dati.zona_climatica == "E"
    assert dati.temperatura_esterna_progetto == -5.0


def test_get_dati_climatici_citta_non_disponibile_solleva_errore():
    with pytest.raises(ValueError):
        get_dati_climatici("Amsterdam")


def test_zone_climatiche_piu_fredde_hanno_temperatura_progetto_piu_bassa():
    """Sanity check: da Palermo (B) a Bolzano (F) la temperatura di
    progetto invernale deve scendere in modo monotono con la severità
    climatica crescente."""
    ordine = ["Palermo", "Napoli", "Roma", "Milano", "Bolzano"]
    temperature = [get_dati_climatici(c).temperatura_esterna_progetto for c in ordine]
    assert temperature == sorted(temperature, reverse=True)


def test_get_trasmittanze_livello_valido():
    trasmittanze = get_trasmittanze("post_2015")
    assert trasmittanze.parete == 0.24


def test_get_trasmittanze_livello_non_disponibile_solleva_errore():
    with pytest.raises(ValueError):
        get_trasmittanze("anni_80")


def test_isolamento_migliora_monotonicamente_nel_tempo():
    """Ogni fascia costruttiva più recente deve avere trasmittanze di
    parete e finestra minori o uguali alla fascia precedente."""
    ordine = ["ante_1976", "1976_1990", "1991_2005", "2006_2015", "post_2015"]
    pareti = [LIVELLI_ISOLAMENTO[k].trasmittanze.parete for k in ordine]
    finestre = [LIVELLI_ISOLAMENTO[k].trasmittanze.finestra for k in ordine]

    assert pareti == sorted(pareti, reverse=True)
    assert finestre == sorted(finestre, reverse=True)


def test_get_profilo_uso_valido():
    profilo = get_profilo_uso("bagno")
    assert profilo.ricambi_aria_orari == 1.5


def test_get_profilo_uso_non_disponibile_solleva_errore():
    with pytest.raises(ValueError):
        get_profilo_uso("garage")


def test_tutte_le_citta_e_i_profili_uso_sono_coerenti():
    assert len(CITTA_DISPONIBILI) >= 5
    assert len(PROFILI_USO) >= 5
