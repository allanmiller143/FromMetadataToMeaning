import json
import csv
import os
import numpy as np
from collections import defaultdict
from scipy.stats import binomtest


# ---------------------------------------------------------------------------
# Reaproveita a lógica de leitura/consenso do script principal
# (mantido self-contido para rodar sozinho na mesma pasta dos dados)
# ---------------------------------------------------------------------------

def compute_metrics(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    return f1


def load_votes(base_path, dataset, evaluators=('p1', 'p2', 'p3')):
    votes = defaultdict(dict)
    for p in evaluators:
        csv_path = os.path.join(base_path, "rotulados", p, f"{dataset}_rotulado.csv")
        if not os.path.exists(csv_path):
            continue
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if not fieldnames:
                continue
            clean_map = {name.strip(): name for name in fieldnames if name}
            id_col = clean_map.get('id')
            match_col = clean_map.get('match_humano')
            if not id_col or not match_col:
                continue
            for row in reader:
                item_id = row[id_col]
                val_raw = row[match_col]
                if not item_id or val_raw is None:
                    continue
                val_clean = val_raw.strip()
                if val_clean not in ('0', '1'):
                    continue
                votes[item_id][p] = int(val_clean)
    return votes


def build_consensus(votes, evaluators=('p1', 'p2', 'p3')):
    consensus = {}
    n_eval = len(evaluators)
    maioria = n_eval // 2 + 1
    for item_id, per_evaluator in votes.items():
        if len(per_evaluator) < n_eval:
            continue
        v_list = [per_evaluator[e] for e in evaluators]
        consensus[item_id] = 1 if sum(v_list) >= maioria else 0
    return consensus


def load_dataset(base_path, ds, evaluators=('p1', 'p2', 'p3')):
    json_path = os.path.join(base_path, "gabarito", f".gabarito_{ds}.json")
    with open(json_path, 'r', encoding='utf-8') as f:
        gabarito = json.load(f)

    votes = load_votes(base_path, ds, evaluators)
    consensus_labels_map = build_consensus(votes, evaluators)

    sims, labs = [], []
    for item_id, data in gabarito.items():
        if item_id in consensus_labels_map:
            sims.append(data['similaridade_real'])
            labs.append(consensus_labels_map[item_id])

    return np.array(sims), np.array(labs)


# ---------------------------------------------------------------------------
# Análise de significância
# ---------------------------------------------------------------------------

def f1_at_threshold(sims, labs, t):
    y_pred = (sims >= t).astype(int)
    return compute_metrics(labs.tolist(), y_pred.tolist())


def bootstrap_best_threshold(sims, labs, thresholds, n_boot=2000, seed=42):
    """
    Reamostra os itens com reposição N vezes e, em cada reamostra, recalcula
    qual threshold maximiza o F1. A distribuição resultante dá um intervalo
    de confiança (IC 95%) para "o quão estável" é o limiar ótimo encontrado.
    """
    rng = np.random.default_rng(seed)
    n = len(sims)
    best_ts = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        s_b, l_b = sims[idx], labs[idx]
        f1s = [f1_at_threshold(s_b, l_b, t) for t in thresholds]
        best_ts[i] = thresholds[int(np.argmax(f1s))]
    ci_low, ci_high = np.percentile(best_ts, [2.5, 97.5])
    return best_ts, ci_low, ci_high


def mcnemar_compare(sims, labs, t1, t2):
    """
    Teste de McNemar (exato, via binomial) comparando o acerto/erro de dois
    thresholds NOS MESMOS itens. Só olha para os itens onde os dois
    thresholds discordam entre si (pares discordantes) e testa se um dos
    dois acerta mais desses casos do que se espera ao acaso (50/50).

    H0: os dois thresholds têm a mesma taxa de acerto.
    p pequeno (< 0.05) => a diferença entre t1 e t2 é estatisticamente
    significativa; p grande => não há evidência de diferença (t1 e t2 são
    estatisticamente equivalentes nesses dados).
    """
    pred1 = (sims >= t1).astype(int)
    pred2 = (sims >= t2).astype(int)
    correct1 = (pred1 == labs)
    correct2 = (pred2 == labs)

    only1 = int(np.sum(correct1 & ~correct2))   # t1 acerta e t2 erra
    only2 = int(np.sum(~correct1 & correct2))   # t2 acerta e t1 erra
    n_disc = only1 + only2

    if n_disc == 0:
        return only1, only2, 1.0

    p = binomtest(only1, n_disc, 0.5).pvalue
    return only1, only2, p


def bootstrap_f1_diff(sims, labs, t1, t2, n_boot=2000, seed=42):
    """
    IC 95% (bootstrap) para a diferença F1(t1) - F1(t2). Se o intervalo
    contém 0, a diferença não é estatisticamente significativa.
    """
    rng = np.random.default_rng(seed)
    n = len(sims)
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        s_b, l_b = sims[idx], labs[idx]
        diffs[i] = f1_at_threshold(s_b, l_b, t1) - f1_at_threshold(s_b, l_b, t2)
    ci_low, ci_high = np.percentile(diffs, [2.5, 97.5])
    return diffs, ci_low, ci_high


def analisar(nome, sims, labs, thresholds, t_referencia=0.50, t_otimo=None):
    print(f"\n=== {nome} ===")
    print(f"n = {len(sims)} itens")

    if t_otimo is None:
        f1s = [f1_at_threshold(sims, labs, t) for t in thresholds]
        t_otimo = thresholds[int(np.argmax(f1s))]

    _, ci_low, ci_high = bootstrap_best_threshold(sims, labs, thresholds)
    dentro = ci_low <= t_referencia <= ci_high
    print(f"Limiar ótimo (F1) nos dados observados: {t_otimo:.2f}")
    print(f"IC 95% (bootstrap) do limiar ótimo: [{ci_low:.2f}, {ci_high:.2f}]")
    print(f"{t_referencia:.2f} está {'DENTRO' if dentro else 'FORA'} do IC 95%")

    only_ref, only_opt, p = mcnemar_compare(sims, labs, t_referencia, t_otimo)
    print(f"McNemar {t_referencia:.2f} vs {t_otimo:.2f}: "
          f"acertos exclusivos de {t_referencia:.2f}={only_ref}, "
          f"exclusivos de {t_otimo:.2f}={only_opt}, p-valor={p:.4f}")

    _, dlow, dhigh = bootstrap_f1_diff(sims, labs, t_referencia, t_otimo)
    print(f"IC 95% da diferença F1({t_referencia:.2f}) - F1({t_otimo:.2f}): [{dlow:.4f}, {dhigh:.4f}]")

    sig = p < 0.05
    print(f"=> Diferença {'SIGNIFICATIVA' if sig else 'NÃO significativa'} (alfa=0.05)")


def main():
    base_path = os.path.dirname(os.path.abspath(__file__))
    datasets = ["magento2", "nhanes", "teixeira"]
    evaluators = ('p1', 'p2', 'p3')
    thresholds = np.round(np.arange(0.0, 1.01, 0.01), 2)

    all_sims, all_labs = [], []

    for ds in datasets:
        sims, labs = load_dataset(base_path, ds, evaluators)
        if len(sims) == 0:
            print(f"Aviso: sem dados de consenso para {ds}, pulando.")
            continue
        all_sims.append(sims)
        all_labs.append(labs)
        analisar(ds, sims, labs, thresholds)

    if all_sims:
        all_sims_g = np.concatenate(all_sims)
        all_labs_g = np.concatenate(all_labs)
        analisar("GLOBAL (agregado)", all_sims_g, all_labs_g, thresholds)


if __name__ == "__main__":
    main()
