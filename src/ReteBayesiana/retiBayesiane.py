# ==============================================================================
# retiBayesiane.py
#
#
#
# Funzionalità principali:
#   Costruzione rete bayesiana di base
#   Apprendimento dei parametri da dataset
#   Inferenza probabilistica sul nodo “Successo”
# ==============================================================================

import logging
from typing import Dict, Optional, List, Any
import pandas as pd
from pgmpy.factors.discrete import TabularCPD
import bnlearn

# ==============================================================================
# Configurazione Logger
# ==============================================================================
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# ==============================================================================
# Classe BayesianaRicette
# ==============================================================================
class BayesianaRicette:
    """
    Classe che gestisce la costruzione, l’apprendimento e l’inferenza
    di una rete bayesiana per stimare il successo di una ricetta.
    """

    # --------------------------------------------------------------------------
    # Inizializzazione
    # --------------------------------------------------------------------------
    def __init__(self, structure: Optional[List[tuple]] = None):
        """
        Inizializza la rete bayesiana.
        :param structure: (opzionale) lista di archi (es. [('Tempo','Successo'), ...])
        """
        # Struttura base (tutti i nodi puntano a Successo)
        self.Bordi = structure or [
            ('Tempo', 'Successo'),
            ('Difficolta', 'Successo'),
            ('QualitaIngredienti', 'Successo')
        ]

        # Crea CPD di default
        self._create_default_cpd()

        # Costruisce il DAG
        try:
            self.DAG = bnlearn.make_DAG(
                self.Bordi,
                CPD=[self.CPD_tempo, self.CPD_difficolta, self.CPD_qualita, self.CPD_successo],
                verbose=0
            )
        except Exception as e:
            logger.warning(f"⚠️ Impossibile creare DAG con CPD iniziali: {e}. Creo DAG vuoto.")
            self.DAG = bnlearn.make_DAG(self.Bordi, verbose=0)

    # --------------------------------------------------------------------------
    # Creazione CPD di default
    # --------------------------------------------------------------------------
    def _create_default_cpd(self) -> None:
        """Crea le CPD di default per ciascuna variabile."""

        # Tutti gli stati sono stringhe ('0', '1', '2')
        self.CPD_tempo = TabularCPD(
            variable='Tempo',
            variable_card=3,
            values=[[0.5], [0.3], [0.2]],
            state_names={'Tempo': ['0', '1', '2']}
        )

        self.CPD_difficolta = TabularCPD(
            variable='Difficolta',
            variable_card=3,
            values=[[0.5], [0.4], [0.1]],
            state_names={'Difficolta': ['0', '1', '2']}
        )

        self.CPD_qualita = TabularCPD(
            variable='QualitaIngredienti',
            variable_card=2,
            values=[[0.3], [0.7]],
            state_names={'QualitaIngredienti': ['0', '1']}
        )

        # --- Genera la CPD di Successo in base a regole euristiche ---
        def genera_cpd_successo():
            valori = [[], []]  # [fallimento, successo]
            for tempo in range(3):
                for diff in range(3):
                    for qualita in range(2):
                        rischio = 0.0
                        # penalizza se poco tempo e difficoltà alta
                        if tempo == 0 and diff > 0:
                            rischio += 0.3 * diff
                        # penalizza la difficoltà
                        if diff == 2:
                            rischio += 0.5
                        elif diff == 1:
                            rischio += 0.2
                        # penalizza la bassa qualità ingredienti
                        if qualita == 0:
                            rischio += 0.4

                        # Limita rischio in [0.1, 0.95]
                        prob_successo = max(0.1, min(0.95, 1.0 - rischio))
                        valori[0].append(1 - prob_successo)  # fallimento
                        valori[1].append(prob_successo)      # successo
            return valori

        self.CPD_successo = TabularCPD(
            variable='Successo',
            variable_card=2,
            values=genera_cpd_successo(),
            evidence=['Tempo', 'Difficolta', 'QualitaIngredienti'],
            evidence_card=[3, 3, 2],
            state_names={
                'Successo': ['0', '1'],
                'Tempo': ['0', '1', '2'],
                'Difficolta': ['0', '1', '2'],
                'QualitaIngredienti': ['0', '1']
            }
        )

    # --------------------------------------------------------------------------
    # Apprendimento da dataset
    # --------------------------------------------------------------------------
    def impara_dataset(self, dataset: pd.DataFrame, metodo: str = "bayes") -> None:
        """
        Apprende i parametri della rete a partire da un dataset.
        :param dataset: DataFrame con colonne ['Tempo', 'Difficolta', 'QualitaIngredienti', 'Successo']
        :param metodo: 'bayes' o 'mle'
        """
        if not isinstance(dataset, pd.DataFrame):
            raise ValueError("❌ Il dataset deve essere un pandas.DataFrame")

        logger.info("📊 Avvio apprendimento parametri dalla tabella dei dati...")

        colonne = list(dataset.columns)
        if 'Successo' not in colonne:
            logger.warning("⚠️ Il dataset non contiene la colonna 'Successo' necessaria per l'apprendimento.")

        # Crea struttura coerente con il dataset
        self.Bordi = [(c, 'Successo') for c in colonne if c != 'Successo']

        try:
            self.DAG = bnlearn.make_DAG(self.Bordi, verbose=0)
        except Exception as e:
            logger.error(f"Errore nella creazione del DAG: {e}")
            raise

        # Converti i valori in stringhe (bnlearn usa categorie testuali)
        df_learn = dataset.copy()
        for col in df_learn.columns:
            df_learn[col] = df_learn[col].apply(
                lambda v: str(int(v)) if pd.notna(v) and isinstance(v, (int, float)) else str(v)
            )

        try:
            self.DAG = bnlearn.parameter_learning.fit(self.DAG, df_learn, methodtype=metodo, verbose=0)
            logger.info("✅ Parametri della rete bayesiana aggiornati con successo.")
        except Exception as e:
            logger.error(f"❌ Errore durante il parameter learning: {e}")
            raise

    # --------------------------------------------------------------------------
    # Inferenza sul nodo Successo
    # --------------------------------------------------------------------------
    def inferenza(self, evidenze: Dict[str, Any]):
        """
        Esegue inferenza sul nodo 'Successo' dato un dizionario di evidenze.
        :param evidenze: es. {'Tempo': 1, 'Difficolta': 0, 'QualitaIngredienti': 1}
        :return: oggetto DiscreteFactor con la distribuzione di 'Successo'
        """
        if not isinstance(evidenze, dict):
            raise ValueError("L'argomento 'evidenze' deve essere un dizionario")

        # Converte tutti i valori in stringhe (per compatibilità con bnlearn)
        evidenze_ok = {}
        for k, v in evidenze.items():
            if pd.isna(v):
                continue
            evidenze_ok[k] = str(int(v)) if isinstance(v, (int, float)) else str(v)

        try:
            # Esegui inferenza bayesiana
            query = bnlearn.inference.fit(
                self.DAG,
                variables=['Successo'],
                evidence=evidenze_ok,
                verbose=0
            )

            # Estrai il fattore di probabilità del nodo "Successo"
            factor = None
            if isinstance(query, dict):
                for chiave in query.keys():
                    if chiave.lower() == 'successo':
                        factor = query[chiave]
                        break
            else:
                factor = query

            if factor is None:
                raise KeyError("Il nodo 'Successo' non è stato trovato nel risultato.")

            # Stampa probabilità se disponibili
            if hasattr(factor, 'values') and len(factor.values) >= 2:
                logger.info(f"P(Successo=0)={factor.values[0]:.3f}, P(Successo=1)={factor.values[1]:.3f}")

            return factor

        except Exception as e:
            logger.error(f"❌ Errore durante l'inferenza (bnlearn): {e}")
            logger.debug(f"Evidenze passate (stringify): {evidenze_ok}")
            raise


# ==============================================================================
# Funzione helper: converte il risultato in DataFrame
# ==============================================================================
def ottieni_risultato_query(query) -> pd.DataFrame:
    """
    Converte il risultato di bnlearn.inference.fit in un DataFrame leggibile.
    """
    try:
        return bnlearn.bnlearn.query2df(query, verbose=0)
    except Exception:
        try:
            if isinstance(query, dict) and 'Successo' in query and hasattr(query['Successo'], 'df'):
                return query['Successo'].df
        except Exception:
            pass
    return pd.DataFrame()
