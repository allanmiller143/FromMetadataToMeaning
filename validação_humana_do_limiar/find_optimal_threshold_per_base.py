import json
import csv
import os
import numpy as np
import matplotlib.pyplot as plt


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


def load_dataset(base_path, ds):
    """Carrega similaridades e rótulos humanos de UMA base específica."""
    json_path = os.path.join(base_path, "gabarito", f".gabarito_{ds}.json")
    csv_path = os.path.join(base_path, "rotulados", f"{ds}_rotulado.csv")

    if not os.path.exists(json_path) or not os.path.exists(csv_path):
        print(f"Aviso: Arquivos para {ds} não encontrados.")
        return [], []

    with open(json_path, "r", encoding="utf-8-sig") as f:
        gabarito = json.load(f)

    similarities, labels = [], []
    skipped = 0

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = row["id"]
            raw_label = (row.get("match_humano") or "").strip()

            if item_id not in gabarito:
                continue
            if raw_label not in ("0", "1"):
                skipped += 1
                continue

            similarities.append(gabarito[item_id]["similaridade_real"])
            labels.append(int(raw_label))

    if skipped:
        print(f"  Aviso ({ds}): {skipped} linha(s) com match_humano vazio/inválido foram ignoradas.")

    return similarities, labels


def sweep_thresholds(similarities, labels, step=0.01):
    """Varre thresholds de 0 a 1 e retorna todos os resultados + o melhor por F1."""
    thresholds = np.arange(0.0, 1.0 + step, step)
    results = []
    best_f1, best_threshold, best_metrics = -1, 0.5, {}

    for t in thresholds:
        y_pred = [1 if s >= t else 0 for s in similarities]
        f1, acc, prec, rec = compute_metrics(labels, y_pred)
        results.append([round(float(t), 2), f1, acc, prec, rec])

        if f1 > best_f1:
            best_f1 = f1
            best_threshold = round(float(t), 2)
            best_metrics = {"f1": f1, "acc": acc, "prec": prec, "rec": rec}

    return results, best_threshold, best_metrics


def main():
    base_path = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_path, "metricas")
    os.makedirs(output_path, exist_ok=True)

    datasets = ["magento2", "nhanes", "teixeira"]
    summary_rows = []
    per_dataset_f1 = {}

    for ds in datasets:
        print(f"\n>>> Processando base: {ds}")
        similarities, labels = load_dataset(base_path, ds)

        if not similarities:
            print(f"  Nenhum dado válido para {ds}, pulando.")
            continue

        n_pos = sum(labels)
        n_total = len(labels)
        print(f"  {n_total} pares rotulados ({n_pos} match, {n_total - n_pos} não-match)")

        results, best_threshold, best_metrics = sweep_thresholds(similarities, labels)

        # Salva CSV individual da base
        csv_file = os.path.join(output_path, f"metricas_thresholds_{ds}.csv")
        with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Threshold", "F1-Score", "Accuracy", "Precision", "Recall"])
            writer.writerows(results)

        per_dataset_f1[ds] = results

        summary_rows.append({
            "base": ds,
            "n_pares": n_total,
            "n_match": n_pos,
            "melhor_threshold": best_threshold,
            "f1": best_metrics["f1"],
            "accuracy": best_metrics["acc"],
            "precision": best_metrics["prec"],
            "recall": best_metrics["rec"],
        })

        print(f"  LIMIAR OTIMO ({ds}): {best_threshold:.2f} | F1: {best_metrics['f1']:.3f} "
              f"| Acc: {best_metrics['acc']:.3f}")

    if not summary_rows:
        print("\nNenhuma base processada. Verifique os caminhos de gabarito/rotulados.")
        return

    # Salva resumo comparativo
    summary_file = os.path.join(output_path, "resumo_melhores_thresholds.csv")
    with open(summary_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Base", "N_Pares", "N_Match", "Melhor_Threshold", "F1", "Accuracy", "Precision", "Recall"])
        for r in summary_rows:
            writer.writerow([r["base"], r["n_pares"], r["n_match"], r["melhor_threshold"],
                              round(r["f1"], 4), round(r["accuracy"], 4),
                              round(r["precision"], 4), round(r["recall"], 4)])

    # Gráfico comparativo: F1 de cada base sobreposto
    plt.figure(figsize=(10, 6))
    colors = {"magento2": "blue", "nhanes": "red", "teixeira": "green"}

    for ds, results in per_dataset_f1.items():
        t_vals = [r[0] for r in results]
        f1_vals = [r[1] for r in results]
        plt.plot(t_vals, f1_vals, label=f"F1 - {ds}", color=colors.get(ds), linewidth=2)

    for r in summary_rows:
        plt.axvline(x=r["melhor_threshold"], color=colors.get(r["base"]), linestyle="--", alpha=0.4)

    plt.axvline(x=0.5, color="black", linestyle="-", alpha=0.6, label="Threshold atual (0.5)")
    plt.title("F1-Score vs Threshold — comparação por base", fontsize=14)
    plt.xlabel("Threshold", fontsize=12)
    plt.ylabel("F1-Score", fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 1)
    plt.ylim(0, 1.05)

    graph_file = os.path.join(output_path, "curva_f1_por_base.png")
    plt.savefig(graph_file, dpi=200)
    plt.close()

    print("\nProcessamento concluído!")
    print(f"CSVs por base salvos em: {output_path}")
    print(f"Resumo comparativo: {summary_file}")
    print(f"Gráfico comparativo: {graph_file}")
    print("\n=== RESUMO ===")
    for r in summary_rows:
        print(f"  {r['base']:<10} -> melhor T={r['melhor_threshold']:.2f} | F1={r['f1']:.3f} | Acc={r['accuracy']:.3f}")


if __name__ == "__main__":
    main()
