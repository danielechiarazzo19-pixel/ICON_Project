# ==============================================================================
# valutazione.py
#
# Script di validazione e valutazione per la rete bayesiana
# "Consulente di Ricette".
#
# Funzionalità:
#   - Carica il dataset CSV delle ricette
#   - Esegue una K-Fold Cross Validation
#   - Addestra e valuta la rete bayesiana su ciascun fold
#   - Calcola e stampa metriche (Accuracy, Precision, Recall, F1)
#   - Salva i risultati in formato CSV e JSON
# ==============================================================================

import os
import json
import logging
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# ==============================================================================
# Import della rete bayesiana
# ==============================================================================
try:
    from retiBayesiane import BayesianaRicette
except ImportError:
    print("❌ ERRORE: impossibile importare 'BayesianaRicette' da retiBayesiane.py")
    exit(1)

# ==============================================================================
# Configurazione Logging
# ==============================================================================
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("valutazione")

# ==============================================================================
# Caricamento Dataset
# ==============================================================================
dataset_path = r"C:\sviluppo\ICON_DanieleChiarazzo\src\ClassiSupporto\dataset_ricette.csv"

if not os.path.exists(dataset_path):
    logger.error(f"❌ File non trovato: {dataset_path}")
    exit(1)

try:
    df = pd.read_csv(dataset_path)
    logger.info(f"✅ Dataset caricato con successo ({df.shape[0]} righe, {df.shape[1]} colonne)")
except Exception as e:
    logger.error(f"Errore durante la lettura del CSV: {e}")
    exit(1)

# ==============================================================================
# Verifica Colonne Richieste
# ==============================================================================
colonne_necessarie = ['Tempo', 'Difficolta', 'QualitaIngredienti', 'Successo']
colonne_presenti = [c for c in colonne_necessarie if c in df.columns]

if len(colonne_presenti) < len(colonne_necessarie):
    logger.warning(f"⚠️ Colonne mancanti. Verranno usate solo: {colonne_presenti}")
    df = df[colonne_presenti]

# ==============================================================================
# Definizione Domini Variabili (per gestire stati mancanti)
# ==============================================================================
DOMINI = {
    'Tempo': [0, 1, 2],
    'Difficolta': [0, 1, 2],
    'QualitaIngredienti': [0, 1],
    'Successo': [0, 1]
}

# ==============================================================================
# Preparazione Dati
# ==============================================================================
X_data = df.drop('Successo', axis=1)
y_data = df['Successo']

# ==============================================================================
# Impostazione K-Fold Cross Validation
# ==============================================================================
N_SPLITS = 10 if len(df) >= 10 else len(df)
kf = KFold(n_splits=N_SPLITS, shuffle=True, random_state=42)

# Liste metriche globali
fold_metrics = []
accuracies, precisions, recalls, f1s = [], [], [], []

logger.info(f"🚀 Avvio della Cross-Validation ({N_SPLITS} fold)...")

# ==============================================================================
# Loop sui Fold
# ==============================================================================
for fold, (train_index, test_index) in enumerate(kf.split(X_data)):
    logger.info(f"--- Fold {fold + 1}/{N_SPLITS} ---")

    X_train, X_test = X_data.iloc[train_index], X_data.iloc[test_index]
    y_train, y_test_true = y_data.iloc[train_index], y_data.iloc[test_index]

    # Combina dati in un unico DataFrame
    train_data_fold = pd.concat([X_train, y_train.rename('Successo')], axis=1)

    # 🔹 Aggiungi stati mancanti per garantire copertura completa
    for col, stati_possibili in DOMINI.items():
        valori_presenti = train_data_fold[col].unique().tolist()
        mancanti = [v for v in stati_possibili if v not in valori_presenti]
        if mancanti:
            for val in mancanti:
                dummy_row = {c: train_data_fold[c].iloc[0] for c in train_data_fold.columns}
                dummy_row[col] = val
                train_data_fold = pd.concat([train_data_fold, pd.DataFrame([dummy_row])], ignore_index=True)
            logger.info(f"📊 Aggiunti stati mancanti per '{col}': {mancanti}")

    # ==============================================================================
    # Addestramento Rete
    # ==============================================================================
    bn_model = BayesianaRicette()
    bn_model.impara_dataset(train_data_fold, metodo="bayes")

    # ==============================================================================
    # Inferenza
    # ==============================================================================
    y_pred_list = []

    for i, test_row in X_test.iterrows():
        evidenza = test_row.to_dict()
        try:
            query_result = bn_model.inferenza(dati=evidenza)
            prob_values = query_result.values

            # Probabilità di Successo=1
            prob_successo_1 = 0.0
            if len(prob_values) == 2:
                prob_successo_1 = prob_values[1]
            elif len(prob_values) == 1:
                prob_successo_1 = 0.0 if '0' in query_result.state_names.get('Successo', []) else 1.0

            predizione = int(prob_successo_1 >= 0.5)
            y_pred_list.append(predizione)

            logger.info(
                f"🔹 Test {i}: evidenza={evidenza} → "
                f"P(Successo=1)={prob_successo_1:.2f} → pred={predizione}"
            )

        except Exception as e:
            logger.error(f"Errore durante l'inferenza nel fold {fold + 1}: {e}")
            y_pred_list.append(np.nan)

    # ==============================================================================
    # Calcolo Metriche
    # ==============================================================================
    y_test_clean = [y for i, y in enumerate(y_test_true) if not np.isnan(y_pred_list[i])]
    y_pred_clean = [y for y in y_pred_list if not np.isnan(y)]

    if len(y_pred_clean) > 0:
        acc = accuracy_score(y_test_clean, y_pred_clean)
        prec = precision_score(y_test_clean, y_pred_clean, pos_label=1, zero_division=0)
        rec = recall_score(y_test_clean, y_pred_clean, pos_label=1, zero_division=0)
        f1 = f1_score(y_test_clean, y_pred_clean, pos_label=1, zero_division=0)

        accuracies.append(acc)
        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

        fold_metrics.append({
            "Fold": fold + 1,
            "Accuracy": round(acc, 3),
            "Precision": round(prec, 3),
            "Recall": round(rec, 3),
            "F1": round(f1, 3)
        })
    else:
        logger.warning(f"⚠️ Nessuna predizione valida per il fold {fold + 1}.")

# ==============================================================================
# Risultati Finali
# ==============================================================================
media_acc = np.mean(accuracies) if accuracies else 0
media_prec = np.mean(precisions) if precisions else 0
media_rec = np.mean(recalls) if recalls else 0
media_f1 = np.mean(f1s) if f1s else 0

print("\n" + "=" * 60)
print("--- Risultati Finali della Cross-Validation ---")
print(f"🎯 Accuracy:  {media_acc:.2f} ± {np.std(accuracies):.2f}")
print(f"🎯 Precision: {media_prec:.2f} ± {np.std(precisions):.2f}")
print(f"🎯 Recall:    {media_rec:.2f} ± {np.std(recalls):.2f}")
print(f"🎯 F1-Score:  {media_f1:.2f} ± {np.std(f1s):.2f}")
print("=" * 60)

# ==============================================================================
# Salvataggio Risultati
# ==============================================================================
output_dir = r"C:\sviluppo\ICON_DanieleChiarazzo\risultati"
os.makedirs(output_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
csv_path = os.path.join(output_dir, f"valutazione_{timestamp}.csv")
json_path = os.path.join(output_dir, f"valutazione_{timestamp}.json")

# --- CSV ---
df_risultati = pd.DataFrame(fold_metrics)
df_risultati.to_csv(csv_path, index=False)

# --- JSON ---
risultato_completo = {
    "media": {
        "Accuracy": round(media_acc, 3),
        "Precision": round(media_prec, 3),
        "Recall": round(media_rec, 3),
        "F1": round(media_f1, 3)
    },
    "folds": fold_metrics
}
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(risultato_completo, f, indent=4)

logger.info(f"📁 Risultati salvati in:\n - CSV:  {csv_path}\n - JSON: {json_path}")

print("\n✅ Valutazione completata. "
      "Puoi ora inserire i risultati nella Sezione 4.4 della tua relazione 📘")

