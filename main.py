# ==============================================================================
# main.py
#
# Punto di ingresso del sistema esperto "Consulente di Ricette".
# Gestisce:
#   - l'avvio del modulo principale (consulenteRicette),
#   - la configurazione del logging,
#   - il ciclo di esecuzione che permette all’utente di fare più consulenze.
#
# 
# ==============================================================================

# ------------------------------------------------------------------------------
# Import principali
# ------------------------------------------------------------------------------
import logging

# ------------------------------------------------------------------------------
# Configurazione del logging
# ------------------------------------------------------------------------------
# Imposta il formato e il livello di dettaglio dei messaggi.
# Puoi passare a logging.DEBUG se vuoi vedere messaggi più dettagliati.
logging.basicConfig(
    level=logging.INFO,  # Livello minimo: mostra info, warning, error
    format='[%(levelname)s] %(message)s',  # Formato messaggio
    handlers=[logging.StreamHandler()]  # Mostra in console
)

# Riduce l’output “rumoroso” di librerie esterne
logging.getLogger("pgmpy").setLevel(logging.ERROR)
logging.getLogger("experta").setLevel(logging.WARNING)

# ------------------------------------------------------------------------------
# Import del sistema esperto vero e proprio
# ------------------------------------------------------------------------------
from src.SistemaEsperto import consulenteRicette


# ------------------------------------------------------------------------------
# Funzione di avvio singola consulenza
# ------------------------------------------------------------------------------
def avvia_sistema():
    """
    Avvia una singola sessione del sistema esperto (una consulenza).
    """
    consulenteRicette.avvia_consulente_ricette()


# ------------------------------------------------------------------------------
# Funzione principale (loop del programma)
# ------------------------------------------------------------------------------
def main():
    """
    Gestisce il ciclo principale del programma:
    - avvia il sistema di consulenza;
    - cattura eventuali errori imprevisti;
    - chiede all’utente se desidera effettuare una nuova consulenza.
    """
    logging.info("Sistema di Consulenza Ricette avviato. Benvenuto!")

    while True:
        try:
            # 🔹 Avvio della consulenza principale
            avvia_sistema()

        except Exception as e:
            # 🔴 Blocco di sicurezza: cattura qualsiasi eccezione non gestita
            logging.error(f"Si è verificato un errore imprevisto: {e}")
            logging.error("Il sistema verrà riavviato automaticamente.")

        # 🔹 Domanda finale all’utente
        print("\n" + "=" * 40)
        risposta = ""
        while risposta not in ['s', 'n']:
            risposta = input("Vuoi avviare una nuova consulenza? (s/n): ").strip().lower()

        if risposta == 'n':
            logging.info("Grazie per aver usato il sistema. Arrivederci! 👋")
            break  # Esce dal loop principale

        # 🔁 Se l’utente risponde “s”, si riparte da capo
        logging.info("Avvio di una nuova consulenza...")


# ------------------------------------------------------------------------------
# Punto di ingresso dell’applicazione
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
