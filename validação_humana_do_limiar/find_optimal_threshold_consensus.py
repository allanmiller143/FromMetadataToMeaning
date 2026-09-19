import json
import csv
import os
import numpy as np
from collections import defaultdict
from statsmodels.stats.inter_rater import fleiss_kappa


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


def load_votes(base_path, dataset, evaluators=('p1', 'p2', 'p3')):
    """
    Lê os arquivos de rotulagem de N avaliadores e retorna, por item_id,
    a lista de votos (0/1) na ordem dos avaliadores. Itens com valores
    ausentes ou inválidos em qualquer avaliador não entram na lista.
    """
    votes = defaultdict(dict)  # item_id -> {evaluator: voto}

    for p in evaluators:
        csv_path = os.path.join(base_path, "rotulados", p, f"{dataset}_rotulado.csv")
        if not os.path.exists(csv_path):
            print(f"Aviso: Arquivo não encontrado para avaliador {p} na base {dataset}: {csv_path}")
            continue

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if not fieldnames:
                continue

            clean_map = {name.strip(): name for name in fieldnames if name}

            if 'id' not in clean_map:
                print(f"ERRO: Coluna 'id' não encontrada no arquivo {csv_path}. Colunas: {fieldnames}")
                continue

            id_col = clean_map['id']
            match_col = clean_map.get('match_humano')

            if not match_col:
                print(f"ERRO: Coluna 'match_humano' não encontrada no arquivo {csv_path}")
                continue

            for row in reader:
                item_id = row[id_col]
                val_raw = row[match_col]

                if not item_id or val_raw is None:
                    continue

                val_clean = val_raw.strip()
                if val_clean == '':
                    continue

                if val_clean not in ('0', '1'):
                    print(f"Aviso: Valor inválido '{val_raw}' para o item {item_id} no arquivo {csv_path}. Ignorado.")
                    continue

                votes[item_id][p] = int(val_clean)

    return votes, evaluators


def build_consensus(votes, evaluators):
    """
    Voto majoritário exigindo que TODOS os avaliadores tenham rotulado o item.
    Itens incompletos são descartados (não entram no gabarito consolidado).
    """
    consensus = {}
    complete_votes = {}  # item_id -> [v1, v2, v3] só dos itens completos

    n_eval = len(evaluators)
    maioria = n_eval // 2 + 1

    for item_id, per_evaluator in votes.items():
        if len(per_evaluator) < n_eval:
            print(f"Aviso: item {item_id} tem só {len(per_evaluator)}/{n_eval} votos, excluído do consenso")
            continue
        v_list = [per_evaluator[e] for e in evaluators]
        complete_votes[item_id] = v_list
        consensus[item_id] = 1 if sum(v_list) >= maioria else 0

    return consensus, complete_votes


def compute_fleiss_kappa(complete_votes):
    """
    Recebe {item_id: [v1, v2, v3]} com votos binários e calcula o Fleiss' Kappa.
    Formato exigido pela statsmodels: uma linha por item, colunas = [n_votos_0, n_votos_1].
    """
    if not complete_votes:
        return None

    matrix = []
    for v_list in complete_votes.values():
        matrix.append([v_list.count(0), v_list.count(1)])

    return fleiss_kappa(np.array(matrix))


def best_thresholds_by_f1(similarities, labels, thresholds):
    """
    Varre os thresholds e retorna:
      - lista completa [t, f1, acc, prec, rec]
      - a faixa (platô) de thresholds que atingem o F1 máximo, e o ponto médio dela
    """
    results = []
    for t in thresholds:
        y_pred = [1 if s >= t else 0 for s in similarities]
        f1, acc, prec, rec = compute_metrics(labels, y_pred)
        results.append([t, f1, acc, prec, rec])

    max_f1 = max(r[1] for r in results)
    plateau = [r[0] for r in results if abs(r[1] - max_f1) < 1e-9]
    plateau_mid = (min(plateau) + max(plateau)) / 2

    return results, max_f1, plateau, plateau_mid


def main():
    base_path = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(base_path, "metricas")
    os.makedirs(output_path, exist_ok=True)

    datasets = ["magento2", "nhanes", "teixeira"]
    evaluators = ('p1', 'p2', 'p3')
    thresholds = np.arange(0.0, 1.01, 0.01)

    all_sims_global = []
    all_labs_global = []

    for ds in datasets:
        json_path = os.path.join(base_path, "gabarito", f".gabarito_{ds}.json")
        if not os.path.exists(json_path):
            print(f"Aviso: Gabarito não encontrado para {ds}, pulando...")
            continue

        with open(json_path, 'r', encoding='utf-8') as f:
            gabarito = json.load(f)

        votes, ev = load_votes(base_path, ds, evaluators)
        consensus_labels_map, complete_votes = build_consensus(votes, ev)

        kappa = compute_fleiss_kappa(complete_votes)
        print(f"\n=== {ds} ===")
        print(f"Itens com consenso completo: {len(complete_votes)}")
        print(f"Fleiss' Kappa entre avaliadores: {kappa:.4f}" if kappa is not None else "Fleiss' Kappa: N/A (sem dados)")

        # distribuição de concordância (3-0 vs 2-1), útil para discutir ambiguidade
        unanime = sum(1 for v in complete_votes.values() if sum(v) in (0, len(ev)))
        dividido = len(complete_votes) - unanime
        print(f"Consenso unânime (3-0): {unanime} | Dividido (2-1): {dividido}")

        similarities, labels = [], []
        for item_id, data in gabarito.items():
            if item_id in consensus_labels_map:
                similarities.append(data['similaridade_real'])
                labels.append(consensus_labels_map[item_id])

        if not similarities:
            print(f"Aviso: Nenhum dado de consenso encontrado para a base {ds}.")
            continue

        ds_results, max_f1, plateau, plateau_mid = best_thresholds_by_f1(similarities, labels, thresholds)

        csv_file = os.path.join(output_path, f"metricas_consensus_{ds}.csv")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Threshold", "F1-Score", "Accuracy", "Precision", "Recall"])
            writer.writerows(ds_results)

        print(f"Melhor F1: {max_f1:.4f} | Platô de thresholds: [{min(plateau):.2f}, {max(plateau):.2f}] | Limiar sugerido (ponto médio): {plateau_mid:.3f}")

        all_sims_global.extend(similarities)
        all_labs_global.extend(labels)

    if not all_sims_global:
        print("\nNenhum dado agregado disponível — verifique os gabaritos e rotulações.")
        return

    agg_results, agg_max_f1, agg_plateau, agg_plateau_mid = best_thresholds_by_f1(
        all_sims_global, all_labs_global, thresholds
    )

    agg_csv_file = os.path.join(output_path, "metricas_thresholds_consensus_aggregated.csv")
    with open(agg_csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Threshold", "F1-Score", "Accuracy", "Precision", "Recall"])
        writer.writerows(agg_results)

    print("\n✅ Processamento de consenso concluído!")
    print(f"Arquivos salvos em: {output_path}")
    print(f"\n🌟 Melhor F1 Global (Consenso): {agg_max_f1:.4f}")
    print(f"🌟 Platô de thresholds: [{min(agg_plateau):.2f}, {max(agg_plateau):.2f}]")
    print(f"🌟 Limiar Global sugerido (ponto médio do platô): {agg_plateau_mid:.3f}")


if __name__ == "__main__":
    main()
