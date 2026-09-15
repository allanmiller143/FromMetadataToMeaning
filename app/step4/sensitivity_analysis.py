import os
import json
import numpy as np
import pandas as pd
import unicodedata
from pathlib import Path
from itertools import combinations, product
from collections import defaultdict
from dotenv import load_dotenv
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from scipy.optimize import linear_sum_assignment
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "magento2"
INPUT_DIR = DATA_DIR / "step3_output"
OUTPUT_DIR = DATA_DIR / "step4_output" / 'sensitivity'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODELS = ["MISTRAL", "OPENAI", "DEEPSEEK", "GEMINI"]
EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100
EMB_CACHE = OUTPUT_DIR / "sensitivity_theme_embeddings.npy"

# =========================
# UTILS
# =========================
def load_env():
    load_dotenv(ROOT_DIR / ".env")
    return os.getenv("OPENAI_API_KEY")

def normalize_theme(theme: str) -> str:
    if theme is None:
        return ""
    theme = str(theme)
    normalized = "".join(
        c for c in unicodedata.normalize("NFD", theme)
        if unicodedata.category(c) != "Mn"
    )
    return normalized.lower().strip()

def safe_list(x):
    return x if isinstance(x, list) else []

def load_all_topics_all_runs():
    all_topics = defaultdict(dict)
    found_files = list(INPUT_DIR.glob("table_topics_*.json"))
    for p in found_files:
        name = p.name
        if not name.startswith("table_topics_"):
            continue
        try:
            core = name.replace("table_topics_", "").replace(".json", "")
            parts = core.split("_")
            if len(parts) < 2:
                continue
            model = "_".join(parts[:-1])
            run_str = parts[-1]
            if not run_str.isdigit():
                continue
            run = int(run_str)
            if model not in MODELS:
                continue
            with open(p, "r", encoding="utf-8") as f:
                all_topics[model][run] = json.load(f)
        except Exception:
            pass
    return all_topics

def collect_unique_themes(all_topics):
    unique = set()
    for model, runs in all_topics.items():
        for run, tables in runs.items():
            for topics in tables.values():
                for t in safe_list(topics):
                    nt = normalize_theme(t)
                    if nt:
                        unique.add(nt)
    return sorted(unique)

def get_embeddings(texts: list[str], api_key: str) -> np.ndarray:
    if EMB_CACHE.exists():
        print(f"Carregando embeddings do cache: {EMB_CACHE}")
        return np.load(EMB_CACHE)

    print(f"Gerando embeddings para {len(texts)} temas únicos via API...")
    client = OpenAI(api_key=api_key)
    embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        embeddings.extend([item.embedding for item in resp.data])

    embeddings_array = np.asarray(embeddings, dtype=np.float32)
    np.save(EMB_CACHE, embeddings_array)
    print(f"Embeddings salvos no cache: {EMB_CACHE}")
    return embeddings_array

def build_embedding_lookup(unique_themes, embeddings):
    return {t: embeddings[i] for i, t in enumerate(unique_themes)}

def topics_for(all_topics, model, run, table):
    topics = safe_list(all_topics.get(model, {}).get(run, {}).get(table, []))
    topics = [normalize_theme(t) for t in topics]
    topics = [t for t in topics if t]
    return sorted(set(topics))

# =========================
# SENSITIVITY ANALYSIS
# =========================
def main():
    print("Iniciando Análise de Sensibilidade Otimizada...")
    api_key = load_env()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não encontrada no .env")

    all_topics = load_all_topics_all_runs()
    detected_models = sorted(all_topics.keys())
    all_tables = set()
    for model in all_topics.keys():
        for run in all_topics[model].keys():
            all_tables.update(all_topics[model][run].keys())
    all_tables = sorted(all_tables)

    unique_themes = collect_unique_themes(all_topics)
    emb = get_embeddings(unique_themes, api_key)
    emb_lookup = build_embedding_lookup(unique_themes, emb)

    # --- FASE 1: Pré-computação dos Pareamentos Ótimos ---
    print("\nFase 1: Pré-computando pareamentos ótimos (Linear Sum Assignment)...")
    # Lista de tuplas: (lista_de_similaridades_do_melhor_pareamento, denominador)
    all_pair_results = []

    for table in all_tables:
        for m1, m2 in combinations(detected_models, 2):
            runs_m1 = sorted(all_topics[m1].keys())
            runs_m2 = sorted(all_topics[m2].keys())
            for r1, r2 in product(runs_m1, runs_m2):
                a = topics_for(all_topics, m1, r1, table)
                b = topics_for(all_topics, m2, r2, table)

                n, m = len(a), len(b)
                denom = n + m

                if denom == 0:
                    all_pair_results.append(([], 0, True)) # Caso especial: ambos vazios (Dice=1.0)
                    continue
                if n == 0 or m == 0:
                    all_pair_results.append(([], denom, False)) # Um deles vazio (Dice=0.0)
                    continue

                # Filtra temas que existem no lookup
                list_a = [t for t in a if t in emb_lookup]
                list_b = [t for t in b if t in emb_lookup]

                if not list_a or not list_b:
                    all_pair_results.append(([], denom, False))
                    continue

                # Cálculo da matriz de similaridade e Assignment (Executado apenas UMA vez)
                A = np.vstack([emb_lookup[t] for t in list_a])
                B = np.vstack([emb_lookup[t] for t in list_b])
                S = cosine_similarity(A, B)
                cost = 1.0 - S
                row_ind, col_ind = linear_sum_assignment(cost)

                # Armazena apenas as similaridades do pareamento ótimo
                optimal_sims = [float(S[i, j]) for i, j in zip(row_ind, col_ind)]
                all_pair_results.append((optimal_sims, denom, False))

    # --- FASE 2: Aplicação dos Limiares ---
    print("\nFase 2: Calculando Soft Dice para a curva de sensibilidade...")
    thresholds = np.arange(0.0, 1.05, 0.05)
    results = []

    for thresh in thresholds:
        soft_dice_vals = []

        for sims, denom, is_both_empty in all_pair_results:
            if is_both_empty:
                soft_dice_vals.append(1.0)
                continue

            if denom == 0:
                soft_dice_vals.append(0.0)
                continue

            # Apenas filtra a lista de similaridades pré-computada
            sim_sum = sum(s for s in sims if s >= thresh)
            soft_dice_vals.append(float((2.0 * sim_sum) / denom))

        avg_soft_dice = float(np.mean(soft_dice_vals)) if soft_dice_vals else 0.0
        results.append((thresh, avg_soft_dice))
        print(f"Threshold {thresh:.2f} -> Avg Soft Dice: {avg_soft_dice:.4f}")

    # Plotting
    thresh_axis, dice_axis = zip(*results)
    plt.figure(figsize=(10, 6))
    plt.plot(thresh_axis, dice_axis, marker='o', linestyle='-', color='b', linewidth=2)
    plt.axvline(x=0.5, color='r', linestyle='--', label='Atual (0.5)')
    plt.title("Análise de Sensibilidade: Limiar de Similaridade vs Soft Dice Médio")
    plt.xlabel("Limiar de Similaridade (Threshold)")
    plt.ylabel("Soft Dice Médio (Inter-Modelos)")
    plt.grid(True, alpha=0.3)
    plt.legend()

    out_plot = OUTPUT_DIR / "threshold_sensitivity_curve.png"
    plt.savefig(out_plot, dpi=300)
    plt.close()

    # Save results to CSV
    df = pd.DataFrame(results, columns=["Threshold", "AvgSoftDice"])
    df.to_csv(OUTPUT_DIR / "threshold_sensitivity_results.csv", index=False)

    print(f"\nAnálise concluída!")
    print(f"Gráfico salvo em: {out_plot}")
    print(f"Resultados salvos em: {OUTPUT_DIR / 'threshold_sensitivity_results.csv'}")

if __name__ == "__main__":
    main()
