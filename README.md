Consulente Intelligente per Ricette e Pianificazione Pasti

Questa repository contiene il progetto realizzato per l’esame di Ingegneria della Conoscenza (ICON).
Il sistema sviluppato fornisce consulenze culinarie intelligenti, suggerendo ricette compatibili con gli ingredienti disponibili, le preferenze alimentari e il tempo a disposizione dell’utente.

Architettura del Sistema

Il progetto integra tre componenti principali di Ingegneria della Conoscenza:

Sistema Esperto (Experta)
Utilizza un motore a regole basato su forward chaining per guidare l’interazione con l’utente.
Raccoglie ingredienti, tempo e preferenze alimentari, e determina le possibili ricette compatibili.
In caso di più risultati, chiede all’utente di scegliere; in caso di nessuna corrispondenza, attiva il modulo ontologico.

Ontologia (Owlready2)
Implementata in OWL tramite Protégé e gestita in Python con Owlready2.
Fornisce una base di conoscenza strutturata sulle ricette, consentendo:

il recupero di dettagli e descrizioni;

la ricerca parziale (fallback) quando non si trovano match perfetti.

Rete Bayesiana (bnlearn)
Valuta la probabilità di successo della ricetta suggerita in base a tempo e difficoltà.
Il sistema permette due modalità di inferenza:

Default (a priori) → CPT definite manualmente in base alla conoscenza esperta.

Apprendimento da dataset (a posteriori) → stima automatica delle probabilità condizionate da un file CSV.

Documentazione

La documentazione completa è disponibile nel file:
Documentazione_Progetto_ICON_DanieleChiarazzo.docx

Include:

Descrizione dei moduli e delle librerie;

Struttura logica del sistema;

Esempi di esecuzione e valutazione;

Analisi dei risultati del modello bayesiano.

Studente

Nome: Daniele
Cognome: Chiarazzo
Matricola: 736585
Email istituzionale: d.chiarazzo1@studenti.uniba.it

Repository GitHub:
https://github.com/danielechiarazzo19-pixel/ICON_Project

Installazione dei Requisiti

Assicurati di avere installato Python 3.10+.
Installa tutte le librerie necessarie elencate in requisiti.txt con il comando:

pip install -r requisiti.txt


Se riscontri errori su Windows, prova con:

python.exe -m pip install -r requisiti.txt

Possibili Errori Durante l’Installazione

Se durante l’installazione compare un errore simile a:

AttributeError: module 'collections' has no attribute 'Mapping'


segui questi passaggi:

Apri il file __init__.py del pacchetto indicato nel messaggio di errore.

Trova la riga:

class frozendict(collections.Mapping)


Modificala in:

class frozendict(collections.abc.Mapping)

Avvio del Sistema

Per avviare il consulente intelligente:

python main.py


Durante l’esecuzione, il sistema:

Raccoglie ingredienti, tempo e preferenze.

Suggerisce una o più ricette compatibili.

Esegue una valutazione probabilistica tramite la rete bayesiana.

In caso di mancata corrispondenza, propone alternative tramite ontologia.

Modalità di Test

Puoi anche testare direttamente la valutazione Bayesiana con:

python valutazione.py

Struttura della Repository
ICON_Project/
│
├── main.py                       # Avvio del sistema esperto completo
├── valutazione.py                # Modulo per testare la rete bayesiana
├── sistema_esperto.py            # Motore inferenziale Experta
├── ontologia.py                  # Gestione e interrogazione ontologia
├── bayesiana.py                  # Costruzione e inferenza rete bayesiana
│
├── dataset_ricette.csv           # Dataset per l’apprendimento delle CPT
├── ontologiaRicette.owl          # File OWL dell’ontologia
│
├── requisiti.txt                 # Librerie richieste
└── Documentazione_Progetto_ICON_DanieleChiarazzo.docx  # Documentazione completa