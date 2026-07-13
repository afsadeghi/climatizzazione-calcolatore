import pytest

from calcolatore.thermal_calc import (
    DatiStanza,
    Trasmittanze,
    calcola_carico_stanza,
    calcola_q_trasmissione,
    calcola_q_ventilazione,
)


TRASMITTANZE_ANTE_1976 = Trasmittanze(parete=1.2, copertura=1.5, pavimento=1.2, finestra=5.0)
TRASMITTANZE_CLASSE_A = Trasmittanze(parete=0.24, copertura=0.22, pavimento=0.26, finestra=1.4)


def test_calcolo_a_mano_stanza_20mq_isolamento_scarso():
    """Verifica su un caso calcolabile a mano.

    Stanza 20 m², h 2.7 m, 1 lato esposto, 4 m² di finestre,
    ricambi 0.5 vol/h, interna 20°C, esterna -5°C (ΔT = 25 K).

    lato = sqrt(20) = 4.47214 m
    parete_lorda = 4.47214 * 2.7 = 12.07477 m²
    parete_netta = 12.07477 - 4 = 8.07477 m²
    q_parete = 1.2 * 8.07477 * 25 = 242.243 W
    q_finestre = 5.0 * 4 * 25 = 500 W
    q_trasmissione = 742.243 W

    volume = 20 * 2.7 = 54 m³
    q_ventilazione = 0.34 * 0.5 * 54 * 25 = 229.5 W

    q_totale = 971.743 W
    """
    stanza = DatiStanza(
        nome="Soggiorno",
        superficie=20,
        altezza=2.7,
        num_esposizioni=1,
        superficie_finestre=4,
        ricambi_aria_orari=0.5,
    )

    risultato = calcola_carico_stanza(
        stanza, TRASMITTANZE_ANTE_1976, temperatura_interna=20, temperatura_esterna=-5
    )

    assert risultato.q_trasmissione_w == pytest.approx(742.243, abs=0.01)
    assert risultato.q_ventilazione_w == pytest.approx(229.5, abs=0.01)
    assert risultato.q_totale_w == pytest.approx(971.743, abs=0.01)


def test_isolamento_scarso_disperde_piu_di_classe_a():
    """Stessa stanza, isolamento scarso vs classe A: il rapporto deve avere senso fisico."""
    stanza = DatiStanza(
        nome="Camera",
        superficie=20,
        altezza=2.7,
        num_esposizioni=1,
        superficie_finestre=4,
        ricambi_aria_orari=0.5,
    )

    risultato_scarso = calcola_carico_stanza(
        stanza, TRASMITTANZE_ANTE_1976, temperatura_interna=20, temperatura_esterna=-5
    )
    risultato_classe_a = calcola_carico_stanza(
        stanza, TRASMITTANZE_CLASSE_A, temperatura_interna=20, temperatura_esterna=-5
    )

    # Il carico di trasmissione scarso deve essere sensibilmente maggiore
    # (le U sono circa 5 volte più alte per pareti e finestre).
    assert risultato_scarso.q_trasmissione_w > risultato_classe_a.q_trasmissione_w
    assert risultato_scarso.q_trasmissione_w / risultato_classe_a.q_trasmissione_w > 3

    # La ventilazione non dipende dall'isolamento: deve restare identica.
    assert risultato_scarso.q_ventilazione_w == pytest.approx(risultato_classe_a.q_ventilazione_w)


def test_delta_t_zero_carico_nullo():
    """Se interna == esterna, il carico deve essere zero (nessuna forza motrice termica)."""
    stanza = DatiStanza(
        nome="Ufficio",
        superficie=15,
        altezza=2.7,
        num_esposizioni=2,
        superficie_finestre=3,
    )

    risultato = calcola_carico_stanza(
        stanza, TRASMITTANZE_ANTE_1976, temperatura_interna=20, temperatura_esterna=20
    )

    assert risultato.q_trasmissione_w == 0
    assert risultato.q_ventilazione_w == 0
    assert risultato.q_totale_w == 0


def test_temperatura_esterna_maggiore_di_interna_solleva_errore():
    stanza = DatiStanza(nome="Bagno", superficie=6, altezza=2.7, num_esposizioni=1)

    with pytest.raises(ValueError):
        calcola_carico_stanza(
            stanza, TRASMITTANZE_ANTE_1976, temperatura_interna=20, temperatura_esterna=25
        )


def test_ultimo_piano_e_piano_terra_aggiungono_dispersioni():
    """Una stanza all'ultimo piano e/o a piano terra deve disperdere di più
    della stessa stanza intermedia (senza copertura/pavimento disperdenti)."""
    base = DatiStanza(
        nome="Stanza",
        superficie=20,
        altezza=2.7,
        num_esposizioni=1,
        superficie_finestre=4,
    )
    con_copertura = DatiStanza(**{**base.__dict__, "ultimo_piano": True})
    con_pavimento = DatiStanza(**{**base.__dict__, "piano_terra": True})

    delta_t = 25
    q_base = calcola_q_trasmissione(base, TRASMITTANZE_ANTE_1976, delta_t)
    q_copertura = calcola_q_trasmissione(con_copertura, TRASMITTANZE_ANTE_1976, delta_t)
    q_pavimento = calcola_q_trasmissione(con_pavimento, TRASMITTANZE_ANTE_1976, delta_t)

    assert q_copertura > q_base
    assert q_pavimento > q_base

    # Il contributo aggiuntivo di copertura deve corrispondere a U * A * ΔT.
    atteso_copertura = TRASMITTANZE_ANTE_1976.copertura * base.superficie * delta_t
    assert q_copertura - q_base == pytest.approx(atteso_copertura, abs=0.01)


def test_ventilazione_proporzionale_a_ricambi_aria():
    stanza_std = DatiStanza(
        nome="Cucina", superficie=10, altezza=2.7, num_esposizioni=1, ricambi_aria_orari=0.5
    )
    stanza_doppi_ricambi = DatiStanza(
        nome="Cucina", superficie=10, altezza=2.7, num_esposizioni=1, ricambi_aria_orari=1.0
    )

    q_std = calcola_q_ventilazione(stanza_std, delta_t=20)
    q_doppio = calcola_q_ventilazione(stanza_doppi_ricambi, delta_t=20)

    assert q_doppio == pytest.approx(q_std * 2)
