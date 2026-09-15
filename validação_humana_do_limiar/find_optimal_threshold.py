import json
import csv
import os
import numpy as np
from collections import defaultdict

def compute_metrics(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return f1, accuracy, precision, recall

def main():
    base_path = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_path, "metricas")

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    datasets = ["magento2", "nhanes", "teixeira"]

    # Para salvar métricas individuais por base
    all_dataset_results = {}

    for ds in datasets:
        json_path = os.path.join(base_path, "gabarito", f".gabarito_{ds}.json")
        csv_path = os.path.join(base_path, "rotulados", f"{ds}_rotulado.csv")

        if not os.path.exists(json_path) or not os.path.exists(csv_path):
            continue

        with open(json_path, 'r', encoding='utf-8') as f:
            gabarito = json.load(f)

        similarities = []
        labels = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_id = row['id']
                if item_id in gabarito:
                    similarities.append(gabarito[item_id]['similaridade_real'])
                    labels.append(int(row['match_humano']))

        # Varredura de thresholds para ESTA base
        thresholds = np.arange(0.0, 1.01, 0.01)
        ds_results = []
        for t in thresholds:
            y_pred = [1 if s >= t else 0 for s in similarities]
            f1, acc, prec, rec = compute_metrics(labels, y_pred)
            ds_results.append([t, f1, acc, prec, rec])

        all_dataset_results[ds] = ds_results

    # 1. Salvar CSVs individuais
    for ds, results in all_dataset_results.items():
        csv_file = os.path.join(output_path, f"metricas_{ds}.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Threshold", "F1-Score", "Accuracy", "Precision", "Recall"])
            writer.writerows(results)

    # 2. Salvar CSV Agregado (como antes)
    aggregated_results = []
    thresholds = np.arange(0.0, 1.01, 0.01)

    # Coletar todos os dados de todas as bases para a agregada
    all_sims = []
    all_labs = []
    for ds in datasets:
        json_path = os.path.join(base_path, "gabarito", f".gabarito_{ds}.json")
        csv_path = os.path.join(base_path, "rotulados", f"{ds}_rotulado.csv")
        if os.path.exists(json_path) and os.path.exists(csv_path):
            with open(json_path, 'r', encoding='utf-8') as f: gab = json.load(f)
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['id'] in gab:
                        all_sims.append(gab[row['id']]['similaridade_real'])
                        all_labs.append(int(row['match_humano']))

    for t in thresholds:
        y_pred = [1 if s >= t else 0 for s in all_sims]
        f1, acc, prec, rec = compute_metrics(all_labs, y_pred)
        aggregated_results.append([t, f1, acc, prec, rec])

    agg_csv_file = os.path.join(output_path, "metricas_thresholds_aggregated.csv")
    with open(agg_csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Threshold", "F1-Score", "Accuracy", "Precision", "Recall"])
        writer.writerows(aggregated_results)

    print("Arquivos de métricas individuais e agregados salvos com sucesso!")

if __name__ == "__main__":
    main()
