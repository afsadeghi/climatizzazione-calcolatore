import pytest

from calcolatore.catalogo import CATALOGO_INIZIALE
from calcolatore.climate_data import (
    TEMPERATURA_INTERNA_DEFAULT,
    get_dati_climatici,
    get_trasmittanze,
)
from calcolatore.interface_bridge import InputStanza, converti_stanze
from calcolatore.raccomandazione import (
    DISCLAIMER,
    FLAG_EFFICIENZA_MANCANTE,
    FLAG_POTENZA_MIN_MANCANTE,
    NOTA_TUTTI_SOVRADIMENSIONATI,
    ZonaCarico,
    _ordina_per_preferenza,
    raccomanda_impianti,
    raccomanda_per_zona,
)
from calcolatore.thermal_calc import calcola_carico_edificio
from calcolatore.zoning import raggruppa_in_zone


def _carichi_zone_di_riferimento() -> dict[str, float]:
    """Ricostruisce, dalla pipeline già validata (climate_data +
    thermal_calc + zoning), i carichi esatti delle 3 zone dell'esempio di
    riferimento (5 stanze a Milano, isolamento 1991-2005, max_zone=3),
    così da non ricopiare a mano numeri che potrebbero disallinearsi."""
    stanze_input = [
        InputStanza("Soggiorno", 25.0, 2.7, "S", False, 6.0, "soggiorno"),
        InputStanza("Cucina", 12.0, 2.7, "N", False, 2.0, "cucina"),
        InputStanza("Camera1", 14.0, 2.7, "E", False, 3.0, "camera"),
        InputStanza("Camera2", 14.0, 2.7, "E", False, 3.0, "camera"),
        InputStanza("Bagno", 6.0, 2.7, "N", False, 1.0, "bagno", ultimo_piano=True),
    ]
    dati_stanze, stanze_zonizzazione = converti_stanze(stanze_input)
    trasmittanze = get_trasmittanze("1991_2005")
    dati_clima = get_dati_climatici("Milano")

    risultati = calcola_carico_edificio(
        dati_stanze, trasmittanze, TEMPERATURA_INTERNA_DEFAULT, dati_clima.temperatura_esterna_progetto
    )
    carico_per_stanza_kw = {r.nome: r.q_totale_kw for r in risultati}

    zone = raggruppa_in_zone(stanze_zonizzazione, max_zone=3)
    return {
        zona.nome: sum(carico_per_stanza_kw[nome] for nome in zona.stanze) for zona in zone
    }


def _zone_di_riferimento() -> list[ZonaCarico]:
    carichi = _carichi_zone_di_riferimento()
    return [ZonaCarico(nome=nome, carico_termico_kw=kw) for nome, kw in carichi.items()]


def test_carichi_zona_di_riferimento_coerenti_con_esempio_end_to_end():
    """Sanity check sui numeri di partenza citati nella specifica: Soggiorno
    ~0.85 kW, Cucina+Bagno e Camere ~0.98 kW ciascuna."""
    carichi = _carichi_zone_di_riferimento()
    valori = sorted(carichi.values())

    assert valori[0] == pytest.approx(0.849, abs=0.001)
    assert valori[1] == pytest.approx(0.977, abs=0.001)
    assert valori[2] == pytest.approx(0.984, abs=0.001)


def test_caso_di_riferimento_candidati_per_zona():
    """Per ognuna delle 3 zone di riferimento, verifica quali modelli del
    catalogo risultano candidati e stampa (via -s) la motivazione, per
    ispezione manuale oltre alle asserzioni."""
    zone = _zone_di_riferimento()

    for zona in zone:
        raccomandazione = raccomanda_per_zona(zona, preferenza="bilanciato")
        assert raccomandazione.messaggio_nessun_modello is None
        assert 1 <= len(raccomandazione.candidati) <= 3
        for candidato in raccomandazione.candidati:
            # Tutti i modelli monozona hanno nominale molto più alto di questi
            # carichi molto piccoli: nessuno rientra nel margine ideale 10-30%.
            assert candidato.margine > 1.0
            assert candidato.motivazione


def test_zona_soggiorno_esclude_ftxm35r_sotto_il_minimo_di_modulazione():
    """Il Soggiorno (~0.849 kW) è sotto il potenza_min_kw di FTXM35R
    (0.9 kW): quel modello non deve comparire tra i candidati."""
    zone = {z.nome: z for z in _zone_di_riferimento()}
    zona_soggiorno = next(z for z in zone.values() if z.carico_termico_kw < 0.9)

    raccomandazione = raccomanda_per_zona(zona_soggiorno, preferenza="bilanciato")
    nomi_candidati = [c.modello.modello for c in raccomandazione.candidati]

    assert "Perfera FTXM35R" not in nomi_candidati
    assert "MSZ-HR35VF" in nomi_candidati


def test_alternativa_multizona_proposta_per_edificio_a_3_zone():
    zone = _zone_di_riferimento()
    risultato = raccomanda_impianti(zone, preferenza="bilanciato")

    assert risultato.alternativa_multizona is not None
    assert risultato.alternativa_multizona.numero_zone == 3
    assert risultato.alternativa_multizona.messaggio_nessun_modello is None
    nomi = [c.modello.modello for c in risultato.alternativa_multizona.candidati]
    assert "3MXM52A9 (multisplit fino a 3 zone)" in nomi


def test_zona_singola_non_propone_alternativa_multizona():
    zona = ZonaCarico(nome="Unica", carico_termico_kw=2.0)
    risultato = raccomanda_impianti([zona], preferenza="bilanciato")

    assert risultato.alternativa_multizona is None


def test_nessun_modello_adeguato_per_carico_troppo_alto():
    """Un carico ben oltre il potenza_max_kw di tutti i modelli del
    catalogo (max assoluto: 7.5 kW, FBA71A9) deve produrre il messaggio
    esplicito, non un match forzato."""
    zona = ZonaCarico(nome="Capannone", carico_termico_kw=10.0)

    raccomandazione = raccomanda_per_zona(zona, preferenza="bilanciato")

    assert raccomandazione.candidati == []
    assert raccomandazione.messaggio_nessun_modello is not None
    assert "10.00 kW" in raccomandazione.messaggio_nessun_modello
    assert "0.70-7.50 kW" in raccomandazione.messaggio_nessun_modello


def test_modello_con_seer_scop_mancanti_non_causa_crash_nel_ranking_efficienza():
    """FBA71A9 (SEER/SCOP None) deve comparire come candidato valido per
    capacità con il flag corretto, e l'ordinamento per 'efficienza' non
    deve sollevare eccezioni nonostante il valore mancante."""
    # 5.0 kW supera il potenza_max_kw sia di FTXM35R (4.0) sia di
    # MSZ-HR35VF (3.6): l'unico monozona capace è FBA71A9.
    zona = ZonaCarico(nome="ZonaGrande", carico_termico_kw=5.0)

    raccomandazione = raccomanda_per_zona(zona, preferenza="efficienza")

    assert raccomandazione.messaggio_nessun_modello is None
    assert len(raccomandazione.candidati) == 1
    candidato = raccomandazione.candidati[0]
    assert candidato.modello.modello == "FBA71A9 canalizzabile media prevalenza"
    assert FLAG_EFFICIENZA_MANCANTE in candidato.flags
    assert FLAG_POTENZA_MIN_MANCANTE in candidato.flags


def test_ordina_per_efficienza_mette_in_coda_i_modelli_senza_dati():
    """I modelli con SEER/SCOP noti devono precedere, nell'ordinamento per
    efficienza, quelli senza dati — senza eccezioni per via del None."""
    zona_ftxm = ZonaCarico(nome="Z1", carico_termico_kw=1.0)  # candidata: FTXM35R e MSZ
    zona_fba = ZonaCarico(nome="Z2", carico_termico_kw=5.0)  # candidata: solo FBA71A9

    candidati_con_dati = raccomanda_per_zona(zona_ftxm, preferenza="efficienza").candidati
    candidato_senza_dati = raccomanda_per_zona(zona_fba, preferenza="efficienza").candidati[0]

    misti = candidati_con_dati + [candidato_senza_dati]
    ordinati = _ordina_per_preferenza(misti, "efficienza")

    assert ordinati[-1].modello.modello == "FBA71A9 canalizzabile media prevalenza"


def test_preferenza_costo_ordina_dal_piu_economico():
    zona = ZonaCarico(nome="Z", carico_termico_kw=1.0)  # FTXM35R (medio) e MSZ-HR35VF (economico)

    candidati = raccomanda_per_zona(zona, preferenza="costo").candidati

    assert candidati[0].modello.fascia_prezzo == "economico"


def test_preferenza_non_valida_solleva_errore():
    zona = ZonaCarico(nome="Z", carico_termico_kw=1.0)
    with pytest.raises(ValueError):
        raccomanda_per_zona(zona, preferenza="inventata")

    with pytest.raises(ValueError):
        raccomanda_impianti([zona], preferenza="inventata")


def test_candidati_mai_piu_di_tre():
    zona = ZonaCarico(nome="Z", carico_termico_kw=1.0)
    for preferenza in ("efficienza", "costo", "bilanciato"):
        candidati = raccomanda_per_zona(zona, preferenza=preferenza).candidati
        assert len(candidati) <= 3


def test_disclaimer_presente_e_invariato():
    zona = ZonaCarico(nome="Z", carico_termico_kw=1.0)
    risultato = raccomanda_impianti([zona], preferenza="bilanciato")

    assert risultato.disclaimer == DISCLAIMER
    assert "installatore qualificato" in risultato.disclaimer


def test_catalogo_iniziale_non_modificato_dal_modulo():
    """Guardia di regressione: il modulo non deve mutare il catalogo
    condiviso (nessuna estensione 'a memoria' durante l'uso)."""
    lunghezza_originale = len(CATALOGO_INIZIALE)
    zona = ZonaCarico(nome="Z", carico_termico_kw=1.0)

    raccomanda_impianti([zona], preferenza="bilanciato")

    assert len(CATALOGO_INIZIALE) == lunghezza_originale


def test_fba71a9_non_viene_mai_escluso_per_carico_basso_causa_potenza_min_mancante():
    """Comportamento intenzionale (non un bug): poiché potenza_min_kw di
    FBA71A9 è None/non verificato, il modulo non lo esclude nemmeno per
    un carico molto basso — non potendo affermare con certezza che NON
    lo copra. Resta candidato per capacità, pesantemente sovradimensionato
    e con il flag esplicito di dato non verificato, invece di sparire
    silenziosamente dal matching."""
    zona = ZonaCarico(nome="RipostiglioMinuscolo", carico_termico_kw=0.05)

    raccomandazione = raccomanda_per_zona(zona, preferenza="bilanciato")

    assert raccomandazione.messaggio_nessun_modello is None
    nomi_candidati = [c.modello.modello for c in raccomandazione.candidati]
    assert "FBA71A9 canalizzabile media prevalenza" in nomi_candidati

    candidato_fba = next(
        c for c in raccomandazione.candidati if c.modello.modello == "FBA71A9 canalizzabile media prevalenza"
    )
    assert FLAG_POTENZA_MIN_MANCANTE in candidato_fba.flags


def test_nota_presente_quando_tutti_i_candidati_sono_sovradimensionati():
    """Caso Zona1 (Soggiorno) del riferimento: entrambi i candidati hanno
    margine ben oltre il 30%, quindi la nota deve comparire per suggerire
    l'alternativa multizona o l'accorpamento fisico."""
    zona = ZonaCarico(nome="Soggiorno", carico_termico_kw=0.849)

    raccomandazione = raccomanda_per_zona(zona, preferenza="bilanciato")

    assert raccomandazione.nota == NOTA_TUTTI_SOVRADIMENSIONATI


def test_nota_assente_quando_almeno_un_candidato_e_ben_dimensionato():
    """Con un carico scelto apposta perché FTXM35R/MSZ-HR35VF (nominale
    3.4 kW) rientrino nel margine ideale 10-30% (3.4 / 1.2 = 2.833 kW),
    la nota non deve comparire anche se FBA71A9 resta sovradimensionato."""
    zona = ZonaCarico(nome="ZonaBenDimensionata", carico_termico_kw=3.4 / 1.2)

    raccomandazione = raccomanda_per_zona(zona, preferenza="bilanciato")

    candidati_ideali = [c for c in raccomandazione.candidati if c.dentro_margine_ideale]
    assert candidati_ideali, "il caso di test deve produrre almeno un candidato ben dimensionato"
    assert raccomandazione.nota is None


def test_nota_assente_quando_nessun_modello_adeguato():
    """Se scatta il messaggio 'nessun modello adeguato' (candidati vuoti),
    la nota sui margini elevati non ha senso e deve restare assente."""
    zona = ZonaCarico(nome="Capannone", carico_termico_kw=10.0)

    raccomandazione = raccomanda_per_zona(zona, preferenza="bilanciato")

    assert raccomandazione.candidati == []
    assert raccomandazione.nota is None
