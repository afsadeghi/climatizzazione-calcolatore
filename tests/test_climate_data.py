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


def test_bolzano_e_zona_climatica_e_non_f():
    """Regressione: Bolzano è zona E secondo DPR 412/93 Allegato A
    (elencata insieme a Milano, Torino, Bologna, Venezia), non zona F."""
    assert get_dati_climatici("Bolzano").zona_climatica == "E"


def test_zone_climatiche_piu_fredde_hanno_temperatura_progetto_piu_bassa():
    """Sanity check: da Palermo (B) a Bolzano (E) la temperatura di
    progetto invernale deve scendere in modo monotono con la severità
    climatica crescente.

    Cuneo (zona F) è volutamente escluso da questo confronto: i
    gradi-giorno (che definiscono la zona) e la temperatura minima di
    progetto (UNI 5364) misurano cose diverse — il primo la severità
    cumulata sulla stagione, la seconda il picco di freddo — e non sono
    garantiti monotoni tra loro città per città (Cuneo ha GG più alti di
    Bolzano ma una minima di progetto meno estrema, per via del clima
    continentale di pianura contro quello di fondovalle alpino)."""
    ordine = ["Palermo", "Napoli", "Roma", "Milano", "Bolzano"]
    temperature = [get_dati_climatici(c).temperatura_esterna_progetto for c in ordine]
    assert temperature == sorted(temperature, reverse=True)


def test_gradi_giorno_coerenti_con_lintervallo_della_zona_climatica():
    """I gradi-giorno di ogni città devono ricadere nell'intervallo DPR
    412/93 corrispondente alla zona climatica dichiarata."""
    intervalli_gg = {
        "B": (601, 900),
        "C": (901, 1400),
        "D": (1401, 2100),
        "E": (2101, 3000),
        "F": (3001, float("inf")),
    }
    for dati in CITTA_DISPONIBILI.values():
        minimo, massimo = intervalli_gg[dati.zona_climatica]
        assert minimo <= dati.gradi_giorno <= massimo, dati.citta


def test_cuneo_e_zona_climatica_f():
    dati = get_dati_climatici("Cuneo")
    assert dati.zona_climatica == "F"
    assert dati.gradi_giorno == 3012


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
