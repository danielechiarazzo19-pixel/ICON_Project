# ==============================================================================
# interfacciaConUtente.py
#
# Questo modulo gestisce l'interazione con l'utente per il sistema esperto
# "Consulente Ricette". Si occupa di:
#   - raccogliere ingredienti, tempo e preferenze alimentari
#   - interrogare l’ontologia delle ricette
#   - stimare la probabilità di successo tramite rete bayesiana
# ==============================================================================

# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------
import logging
from owlready2 import *
import pandas as pd
import os
from src.ReteBayesiana import retiBayesiane as rb 

# --------------------------------------------------------------------------
# Configurazione logger
# --------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Variabili globali
# --------------------------------------------------------------------------
ingredienti_disponibili = []
tempo = ""                   # 'poco', 'medio', 'molto'
preferenze = []              # es. ['vegetariano']
reteAggiornata = None        # Oggetto rete bayesiana appresa dal dataset


# ==============================================================================
# 1️⃣ RACCOLTA DATI DALL’UTENTE
# ==============================================================================

def chiedi_ingredienti_disponibili():
    """
    Chiede all’utente di inserire gli ingredienti disponibili.
    Ritorna una lista di stringhe in minuscolo.
    """
    global ingredienti_disponibili
    print("Inserisci gli ingredienti che hai a disposizione, separati da una virgola.")
    risposta = input("(es. pasta, uova, pomodoro, lattuga): ").strip()
    
    if not risposta:
        ingredienti_disponibili = []
        return []
        
    ingredienti_disponibili = [ing.strip().lower() for ing in risposta.split(',')]
    return ingredienti_disponibili


def chiedi_tempo_disponibile():
    """
    Chiede quanti minuti l’utente ha a disposizione e li converte in categoria ('poco', 'medio', 'molto').
    """
    global tempo
    while True:
        try:
            risposta = input("Quanti minuti hai a disposizione? (es. 30): ").strip()
            minuti = int(risposta)
            if minuti <= 0:
                print("Inserisci un numero positivo.")
                continue

            tempo = converti_tempo_in_categoria(minuti)
            logger.debug(f"Minuti {minuti} -> Categoria Tempo: {tempo}")
            return tempo

        except ValueError:
            print("Input non valido. Inserisci un numero intero (es. 30).")


def chiedi_preferenze_alimentari():
    """
    Chiede eventuali preferenze alimentari (es. vegetariano, vegano).
    Ritorna una lista, vuota se non specificate.
    """
    global preferenze
    print("Hai preferenze alimentari particolari? (es. vegetariano, vegano, nessuna)")
    risposta = input("Se più di una, separale con virgola. Premi INVIO se non ne hai: ").strip().lower()

    if not risposta or risposta == "nessuna":
        preferenze = []
        return []
    
    preferenze = [pref.strip() for pref in risposta.split(',')]
    return preferenze


# ==============================================================================
# 2️⃣ INTERAZIONE CON L’ONTOLOGIA DELLE RICETTE
# ==============================================================================

def trova_dettagli_ricetta_in_ontologia(nome_ricetta):
    """
    Cerca i dettagli di una ricetta (tempo, descrizione, alternativa)
    nell’ontologia 'ontologiaRicette.owl'.
    """
    path_ontologia = "./src/Ontologia/ontologiaRicette.owl"
    
    try:
        path = os.path.dirname(os.path.abspath(path_ontologia)).replace("\\", "/")
        path_completo = f"file://{path}/{os.path.basename(path_ontologia)}"
        onto = get_ontology(path_completo).load()
        logger.debug(f"Ontologia caricata da: {path_completo}")
    except Exception as e:
        logger.error(f"Impossibile caricare il file ontologia '{path_ontologia}'. Dettagli: {e}")
        return None

    nome_individuo = nome_ricetta.replace(" ", "_")
    individuo = onto.search_one(iri=f"*{nome_individuo}")

    if individuo is None:
        logger.warning(f"Nessun dettaglio trovato nell'ontologia per '{nome_ricetta}'.")
        return None

    dettagli = {}

    # Tempo di preparazione
    if hasattr(individuo, "haTempoPreparazioneMinuti") and individuo.haTempoPreparazioneMinuti:
        dettagli['tempo'] = individuo.haTempoPreparazioneMinuti[0]
        
    # Descrizione
    if hasattr(individuo, "haDescrizionePassaggi") and individuo.haDescrizionePassaggi:
        dettagli['descrizione'] = individuo.haDescrizionePassaggi[0]
        
    # Alternativa
    try:
        classe_ricetta = individuo.is_a[0]
        altre_ricette = [
            alt.name for alt in classe_ricetta.instances()
            if alt != individuo and hasattr(alt, "name")
        ]
        if altre_ricette:
            dettagli['alternativa'] = altre_ricette[0].replace("_", " ")
    except Exception as e:
        logger.debug(f"Nessuna alternativa trovata. Dettagli: {e}")
            
    return dettagli


def cerca_ricette_parziali(lista_ingredienti):
    """
    Cerca ricette nell’ontologia che contengono almeno uno degli ingredienti forniti.
    """
    logger.debug(f"Ricerca parziale per ingredienti: {lista_ingredienti}")
    path_ontologia = "./src/Ontologia/ontologiaRicette.owl"
    
    try:
        path = os.path.dirname(os.path.abspath(path_ontologia)).replace("\\", "/")
        path_completo = f"file://{path}/{os.path.basename(path_ontologia)}"
        onto = get_ontology(path_completo).load()
    except Exception as e:
        logger.error(f"Errore caricamento ontologia per ricerca parziale: {e}")
        return

    NOME_PROPRIETA_INGREDIENTE = "haIngrediente"
    if not hasattr(onto, NOME_PROPRIETA_INGREDIENTE):
        logger.warning(f"La proprietà '{NOME_PROPRIETA_INGREDIENTE}' non è stata trovata nell'ontologia.")
        return

    ricette_trovate = {}

    for ingrediente in lista_ingredienti:
        try:
            risultati = onto.search(**{NOME_PROPRIETA_INGREDIENTE: ingrediente})
            for ricetta in risultati:
                nome_ricetta = ricetta.name.replace("_", " ")
                ricette_trovate.setdefault(nome_ricetta, []).append(ingrediente)
        except Exception as e:
            logger.warning(f"Errore nella ricerca per '{ingrediente}': {e}")

    if not ricette_trovate:
        logger.info("Nessun suggerimento parziale trovato nell'ontologia.")
    else:
        logger.info("\n--- Suggerimenti Alternativi (basati sui tuoi ingredienti) ---")
        for nome, ingr_match in ricette_trovate.items():
            logger.info(f"  > {nome} (usa: {', '.join(ingr_match)})")
        logger.info("Nota: Potresti aver bisogno di altri ingredienti per completarle.")


# ==============================================================================
# 3️⃣ RETE BAYESIANA — STIMA DI SUCCESSO
# ==============================================================================

def calcola_rischio_o_successo_ricetta(nome_ricetta, fatti):
    """
    Usa la rete bayesiana per stimare la probabilità di successo della ricetta.
    Può apprendere da dataset o usare la rete di default.
    """
    global reteAggiornata

    # Inizializza rete bayesiana
    try:
        rete_bayesiana_temp = rb.BayesianaRicette()
    except Exception as e:
        logger.error(f"Errore nella creazione della rete bayesiana: {e}")
        return "Valutazione non disponibile."

    # Costruisci evidenza per l’inferenza
    evidenza = {}
    if 'tempo' in fatti:
        evidenza['Tempo'] = converti_tempo_in_indice(fatti['tempo'])
    logger.debug(f"Evidenza per Rete Bayesiana: {evidenza}")

    # Scelta modalità (1=default, 2=dataset)
    scelta_rete = ""
    while scelta_rete not in ["1", "2"]:
        print("\nVuoi affinare la stima usando il dataset (se disponibile)?")
        scelta_rete = input("(1) Usa stima di default\n(2) Usa stima con apprendimento da dataset\nRisposta: ").strip()

    rete_da_usare = rete_bayesiana_temp

    if scelta_rete == "2":
        try:
            dataset_path = "src/ClassiSupporto/dataset_ricette.csv"
            dataset = pd.read_csv(dataset_path)
            rete_bayesiana_temp.impara_dataset(dataset, "bayes")
            reteAggiornata = rete_bayesiana_temp
            rete_da_usare = reteAggiornata
            logger.info(f"Rete aggiornata con successo usando '{dataset_path}'")
        except FileNotFoundError:
            logger.warning(f"Dataset '{dataset_path}' non trovato. Uso la rete di default.")
        except Exception as e:
            logger.error(f"Errore durante l'apprendimento dal dataset: {e}. Uso la rete di default.")

    # Esegui inferenza
    try:
        risultato = rb.ottieni_risultato_query(rete_da_usare.inferenza(evidenza))
        p_successo = risultato["Successo"]

        try:
            valore_successo = float(p_successo.iloc[1])     # ✅ Conversione sicura a float
            probabilita_successo = valore_successo * 100
            return f"Probabilità di successo stimata: {round(probabilita_successo, 2)}%"
        except Exception as conv_err:
            logger.error(f"Valore non numerico per la probabilità di successo ({p_successo}). Dettagli: {conv_err}")
            return "Impossibile calcolare la stima."

    except KeyError:
        logger.error("Errore: il nodo 'Successo' non è stato trovato nel risultato.")
        return "Impossibile calcolare la stima."
    except Exception as e:
        logger.error(f"Errore durante l'inferenza Bayesiana: {e}")
        return "Impossibile calcolare la stima."


# ==============================================================================
# 4️⃣ FUNZIONI DI SUPPORTO
# ==============================================================================

def converti_tempo_in_categoria(minuti):
    """Converte i minuti in categorie 'poco', 'medio', 'molto'."""
    if minuti <= 20:
        return "poco"
    elif minuti <= 60:
        return "medio"
    else:
        return "molto"


def converti_tempo_in_indice(categoria_tempo):
    """Converte la categoria tempo in un indice numerico per la rete bayesiana."""
    mapping = {"poco": 0, "medio": 1, "molto": 2}
    return mapping.get(categoria_tempo, 1)  # Default = medio
