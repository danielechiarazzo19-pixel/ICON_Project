# ==============================================================================
# consulenteRicette.py
#
# Questo modulo implementa il motore del sistema esperto per suggerire ricette
# usando la libreria experta. Gestisce l'interazione per raccogliere
# ingredienti, tempo e preferenze.
# ==============================================================================

import logging
from experta import *
from src.ClassiSupporto import interfacciaConUtente 

#  Ottieni un'istanza del logger per questo file ---
logger = logging.getLogger(__name__)

# ==============================================================================
# Classe ConsulenteRicette
# Implementa il motore del sistema esperto.
# ==============================================================================
class ConsulenteRicette(KnowledgeEngine):

    # ... (le prime 4 regole 'DefFacts', 'chiedi_ingredienti', 'chiedi_tempo', 'chiedi_preferenze' sono invariate) ...

    @DefFacts()
    def _initial_action(self):
        yield Fact(azione="chiediIngredienti")

    @Rule(Fact(azione="chiediIngredienti"), salience=10)
    def chiedi_ingredienti(self):
        logger.info("--- Inserimento Ingredienti ---")
        
        ingredienti_utente = interfacciaConUtente.chiedi_ingredienti_disponibili()
        if not ingredienti_utente:
            logger.info("Nessun ingrediente inserito. Impossibile suggerire ricette.")
            self.declare(Fact(azione="termina"))
            return
            
        for ingrediente in ingredienti_utente:
            self.declare(Fact(ingrediente=ingrediente.strip().lower()))
            
        self.declare(Fact(azione="chiediTempo"))

    @Rule(Fact(azione="chiediTempo"), salience=9)
    def chiedi_tempo(self):
        logger.info("\n--- Tempo a Disposizione ---")
        tempo = interfacciaConUtente.chiedi_tempo_disponibile()
        self.declare(Fact(tempo_disponibile=tempo))
        self.declare(Fact(azione="chiediPreferenze"))

    @Rule(Fact(azione="chiediPreferenze"), salience=8)
    def chiedi_preferenze(self):
        logger.info("\n--- Preferenze Alimentari ---")
        prefs = interfacciaConUtente.chiedi_preferenze_alimentari()
        for preferenza in prefs:
            self.declare(Fact(preferenza=preferenza.strip().lower()))
        self.declare(Fact(azione="trovaRicetta"))
        
    # --------------------------------------------------------------------------
    # REGOLE PER TROVARE "CANDIDATI" (Priorità 1)
    # --------------------------------------------------------------------------

    @Rule(Fact(azione="trovaRicetta"),
          Fact(ingrediente="pasta"),
          Fact(ingrediente="pomodoro"),
          OR(Fact(tempo_disponibile="medio"),
             Fact(tempo_disponibile="molto")),
          salience=1) 
    def suggerisci_pasta_pomodoro(self):
        logger.debug("Trovato candidato: Pasta al Pomodoro")
        self.declare(Fact(candidato="Pasta al Pomodoro")) 

    @Rule(Fact(azione="trovaRicetta"),
          Fact(ingrediente="uova"),
          Fact(tempo_disponibile="poco"), 
          salience=1)
    def suggerisci_uova_strapazzate(self):
        logger.debug("Trovato candidato: Uova Strapazzate")
        self.declare(Fact(candidato="Uova Strapazzate"))

    @Rule(Fact(azione="trovaRicetta"),
          Fact(ingrediente="lattuga"),
          Fact(ingrediente="pomodoro"),
          Fact(tempo_disponibile="poco"),
          salience=1)
    def suggerisci_insalata(self):
        logger.debug("Trovato candidato: Insalata Mista")
        self.declare(Fact(candidato="Insalata Mista"))
        
    # --------------------------------------------------------------------------
    #  NUOVA REGOLA PER SCEGLIERE TRA I CANDIDATI (Priorità 0.5) ---
    # Si attiva solo se almeno un candidato è stato trovato.
    # --------------------------------------------------------------------------
    @Rule(Fact(azione="trovaRicetta"),
          Fact(candidato=W()), # Si attiva solo se esiste almeno un candidato
          salience=0.5)
    def scegli_candidati(self):
        # Raccogli tutti i candidati unici
        candidati = set()
        for fact in self.facts.values():
            if 'candidato' in fact:
                candidati.add(fact['candidato'])
        
        candidati_lista = list(candidati)
        
        if len(candidati_lista) == 1:
            # --- Se c'è solo un candidato, sceglilo automaticamente ---
            ricetta_scelta = candidati_lista[0]
            logger.info(f"\nHo trovato un'unica ricetta che corrisponde ai tuoi criteri: {ricetta_scelta}")
        else:
            # --- Se ci sono più candidati, fai scegliere l'utente ---
            logger.info("\nHo trovato più ricette che corrispondono ai tuoi criteri:")
            for i, nome in enumerate(candidati_lista):
                print(f"({i+1}) {nome}") # Usiamo print per l'interazione
            
            scelta = 0
            while scelta < 1 or scelta > len(candidati_lista):
                try:
                    risposta = input(f"Quale ricetta vuoi preparare? (1-{len(candidati_lista)}): ").strip()
                    scelta = int(risposta)
                    if scelta < 1 or scelta > len(candidati_lista):
                        print("Scelta non valida. Inserisci un numero della lista.")
                except ValueError:
                    print("Input non valido. Inserisci un numero.")
            
            ricetta_scelta = candidati_lista[scelta-1]
            logger.info(f"Hai scelto: {ricetta_scelta}")

        # Dichiara la ricetta scelta per far partire la valutazione
        self.declare(Fact(ricetta_suggerita=ricetta_scelta))
        self.declare(Fact(azione="valutaRicetta"))

    # --------------------------------------------------------------------------
    # Regola "di fallback" (Priorità 0) ---
    # Si attiva solo se 'trovaRicetta' è attivo E non è stato trovato NESSUN candidato
    # --------------------------------------------------------------------------
    @Rule(Fact(azione="trovaRicetta"),
          NOT(Fact(candidato=W())), # Si attiva solo se NESSUNA regola 'suggerisci' ha avuto successo
          salience=0) 
    def nessuna_ricetta_trovata(self):
          logger.info("\nMi dispiace, non ho trovato ricette *perfette* che usino tutti i tuoi ingredienti e il tempo a disposizione.")
          logger.info("Provo a cercare nell'ontologia ricette che usano almeno uno degli ingredienti forniti...")
          
          ingredienti_utente = []
          for fact in self.facts.values():
              if 'ingrediente' in fact:
                  ingredienti_utente.append(fact['ingrediente'])
          
          if not ingredienti_utente:
              logger.warning("Nessun ingrediente trovato nei fatti per la ricerca parziale.")
          else:
              interfacciaConUtente.cerca_ricette_parziali(ingredienti_utente)

          self.declare(Fact(azione="termina"))

    @Rule(Fact(azione="valutaRicetta"),
          Fact(ricetta_suggerita=MATCH.ricetta),
          salience=-0.5) # Salience abbassata per essere sicuri che giri dopo la scelta
    def valuta_ricetta_con_bayes(self, ricetta):
        logger.info(f"\n--- Valutazione Ricetta: {ricetta} ---")
        
        fatti_per_bayes = {}
        for fact in self.facts.values():
              if 'tempo_disponibile' in fact:
                    fatti_per_bayes['tempo'] = fact['tempo_disponibile']
              
        rischio_o_successo = interfacciaConUtente.calcola_rischio_o_successo_ricetta(ricetta, fatti_per_bayes)
        
        self.declare(Fact(valutazione_ricetta=rischio_o_successo))
        self.declare(Fact(azione="stampaRisultato"))

    def _stampa_dettagli_ricetta(self, nome_ricetta):
        dettagli_ontologia = interfacciaConUtente.trova_dettagli_ricetta_in_ontologia(nome_ricetta)
        nome_alternativa = None

        if dettagli_ontologia:
            if 'tempo' in dettagli_ontologia:
                logger.info(f"  > Tempo stimato: {dettagli_ontologia['tempo']} minuti")
            if 'descrizione' in dettagli_ontologia:
                logger.info(f"  > Breve descrizione: {dettagli_ontologia['descrizione']}")
            
            if 'alternativa' in dettagli_ontologia:
                nome_alternativa = dettagli_ontologia['alternativa']
        
        return nome_alternativa
    
    @Rule(Fact(azione="stampaRisultato"),
          Fact(ricetta_suggerita=MATCH.ricetta),
          Fact(valutazione_ricetta=MATCH.valutazione), 
          salience=-1) 
    def stampare_risultato_finale(self, ricetta, valutazione):
        logger.info(f"\n--- Consiglio Finale ---")
        logger.info(f"Ricetta Suggerita: {ricetta}")
        logger.info(f"Valutazione: {valutazione}")

        nome_alternativa = self._stampa_dettagli_ricetta(ricetta)

        if nome_alternativa:
            risposta = ""
            while risposta not in ['s', 'n']:
                print(f"\nÈ stata trovata un'alternativa simile: {nome_alternativa}")
                risposta = input("Vuoi vederne i dettagli? (s/n): ").strip().lower()

            if risposta == 's':
                logger.info(f"\n--- Dettagli per {nome_alternativa} ---")
                self._stampa_dettagli_ricetta(nome_alternativa) 

        self.declare(Fact(azione="termina"))

    @Rule(Fact(azione="termina"), salience=-10)
    def terminare_esecuzione(self):
        logger.info("\n============ !!! CONSULENZA TERMINATA !!! =============")

# ==============================================================================
# Funzione per avviare il sistema esperto.
# ==============================================================================
def avvia_consulente_ricette(): 
    sistema = ConsulenteRicette()
    sistema.reset() 
    sistema.run()