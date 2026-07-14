import pytest

from calcolatore.zoning import StanzaPerZonizzazione, raggruppa_in_zone


def _stanze_esempio() -> list[StanzaPerZonizzazione]:
    return [
        StanzaPerZonizzazione("Camera1", esposizione="N", uso="camera"),
        StanzaPerZonizzazione("Camera2", esposizione="N", uso="camera"),
        StanzaPerZonizzazione("Cucina", esposizione="S", uso="cucina"),
        StanzaPerZonizzazione("Bagno", esposizione="S", uso="bagno"),
    ]


def test_lista_vuota_restituisce_nessuna_zona():
    assert raggruppa_in_zone([]) == []


def test_max_zone_capiente_ogni_stanza_e_una_zona_a_se():
    """Con max_zone di default (16) e poche stanze (MVP: fino a 6), ogni
    stanza deve restare una zona indipendente, senza accorpamenti."""
    stanze = _stanze_esempio()
    zone = raggruppa_in_zone(stanze)

    assert len(zone) == len(stanze)
    for zona in zone:
        assert len(zona.stanze) == 1


def test_max_zone_zero_o_negativo_solleva_errore():
    with pytest.raises(ValueError):
        raggruppa_in_zone(_stanze_esempio(), max_zone=0)


def test_accorpa_privilegiando_stanze_con_esposizione_e_uso_comuni():
    """Con max_zone=2, le due camere (stessa esposizione N e stesso uso
    camera, similarità massima) devono finire insieme, così come cucina
    e bagno (stessa esposizione S)."""
    zone = raggruppa_in_zone(_stanze_esempio(), max_zone=2)

    assert len(zone) == 2
    gruppi_stanze = [set(zona.stanze) for zona in zone]
    assert {"Camera1", "Camera2"} in gruppi_stanze
    assert {"Cucina", "Bagno"} in gruppi_stanze


def test_max_zone_uno_accorpa_tutto_in_una_sola_zona():
    zone = raggruppa_in_zone(_stanze_esempio(), max_zone=1)

    assert len(zone) == 1
    assert set(zone[0].stanze) == {"Camera1", "Camera2", "Cucina", "Bagno"}


def test_nessuna_stanza_viene_persa_o_duplicata_negli_accorpamenti():
    stanze = _stanze_esempio()
    zone = raggruppa_in_zone(stanze, max_zone=2)

    nomi_originali = {s.nome for s in stanze}
    nomi_nelle_zone = [nome for zona in zone for nome in zona.stanze]

    assert set(nomi_nelle_zone) == nomi_originali
    assert len(nomi_nelle_zone) == len(nomi_originali)


def test_nome_zona_descrittivo_se_uso_ed_esposizione_uniformi():
    zone = raggruppa_in_zone(_stanze_esempio(), max_zone=2)

    zona_camere = next(z for z in zone if set(z.stanze) == {"Camera1", "Camera2"})
    assert "camera" in zona_camere.nome
    assert "N" in zona_camere.nome
