"""
rq6_token_cost.py
==================
Responde SOMENTE à RQ6 do artigo:

    "What trade-off exists between semantic stability and input-token cost
    across metadata configurations?"

Metodologia igual à das RQ1–RQ5 do artigo (não ao script original):
para cada uma das 26 configurações, comparamos os tópicos extraídos contra
a configuração `full` (v01_full) e convertemos o Soft-Dice em SHIFT (Δ),
usando o piso de ruído intra-modelo (Equação 1 do artigo):

    Δ_m(config, full) = η_{m,dataset} − SoftDice_m(config, full)

O shift é calculado por modelo e depois tirado a média entre os 4 LLMs
(igual ao que as outras RQs reportam). Esse shift médio é então pareado
com o custo médio de tokens de ENTRADA de cada configuração — a peça que
faltava no texto atual da RQ6.

IMPORTANTE — separação por dataset:
O script original não distingue E-SUS de NHANES (ele processa um único
DATA_DIR por vez). O piso de ruído (η) é diferente por dataset, então
esse valor precisa ser escolhido corretamente na CONFIG abaixo (DATASET).
Rode o script uma vez para "esus" e outra para "nhanes" (apontando
DATA_DIR / DATASET para cada base), depois junte os dois CSVs se quiser
uma tabela única no artigo.

v01_full entra na tabela/plot com shift = 0.0 por definição (é a própria
referência), igual ao tratamento dado a ela no script original.

Saídas (em OUTPUT_DIR):
  rq6_token_cost_<DATASET>.csv   ← Configuração | Shift médio | Tokens_in médio
  rq6_token_cost_<DATASET>.png   ← scatter shift x tokens (fronteira de eficiência)
"""

import os
import json
import numpy as np
import pandas as pd
import unicodedata
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
from openai import OpenAI

from sklearn.metrics.pairwise import cosine_similarity
from scipy.optimize import linear_sum_assignment
import matplotlib.pyplot as plt

# =============================================================================
# CONFIG
# =============================================================================

ROOT_DIR = Path(__file__).resolve().parents[4]
DATA_DIR = ROOT_DIR / "data/" / "nhanes"
STEP3_DIR = DATA_DIR / "step3_output"

# >>> AJUSTE AQUI a cada execução: qual dataset este DATA_DIR representa <<<
DATASET = "nhanes"   # "esus" ou "nhanes" — precisa bater com INTRA_MODEL_NOISE abaixo

LLM_MODELS = {
    "OPENAI":   STEP3_DIR / "step3_ablation_openai",
    "DEEPSEEK": STEP3_DIR / "step3_ablation_deepseek",
    "MISTRAL":  STEP3_DIR / "step3_ablation_mistral",
    "GEMINI":   STEP3_DIR / "step3_ablation_gemini",
}

OUTPUT_DIR = STEP3_DIR / "step3_ablation_results_rq6"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100
SIMILARITY_THRESHOLD = 0.5
PLT_STYLE = "seaborn-v0_8-darkgrid"

BASELINE_VARIANT = "v01_full"

VARIANT_ORDER = [
    "v00_baseline", "v01_full", "v02_plus_fk", "v03_plus_nullable",
    "v04_plus_numeric_stats", "v05_plus_sample_values", "v06_plus_frequent_values",
    "v07_plus_sample_rows", "v08_fk_plus_sample_values", "v09_fk_plus_frequent_values",
    "v10_fk_plus_sample_and_frequent", "v11_fk_plus_sample_rows",
    "v12_nullable_plus_sample_values", "v13_nullable_plus_frequent_values",
    "v14_nullable_plus_numeric_stats", "v15_sample_rows_vs_sample_values",
    "v16_sample_rows_vs_frequent_values", "v17_sample_rows_plus_both_values",
    "v18_fk_nullable_sample_values", "v19_fk_nullable_frequent_values",
    "v20_fk_nullable_both_values", "v21_fk_nullable_sample_rows",
    "v22_fk_nullable_sample_rows_plus_frequent",
    "v23_fk_nullable_sample_rows_plus_sample_values",
    "v24_full_no_numeric_stats", "v25_full_no_sample_rows",
]

# =============================================================================
# PISO DE RUÍDO INTRA-MODELO (Tabela "Noise floor" do artigo, η_{m,dataset})
# Gemini não tem run repetido em E-SUS -> excluído da média para esus.
# =============================================================================

INTRA_MODEL_NOISE = {
    "OPENAI":   {"esus": 0.939, "nhanes": 0.917},
    "DEEPSEEK": {"esus": 0.919, "nhanes": 0.923},
    "MISTRAL":  {"esus": 0.896, "nhanes": 0.875},
    "GEMINI":   {"nhanes": 0.861, "esus": 0.861},  
}


# =============================================================================
# UTILS (carregamento de dados — inalterados em relação ao script original)
# =============================================================================

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


def parse_run_from_filename(path: Path):
    stem = path.stem
    parts = stem.split("_")
    if not parts:
        return None
    last = parts[-1]
    return int(last) if last.isdigit() else None


def load_ablation_runs(input_dir: Path):
    all_topics = defaultdict(dict)
    for variant_dir in input_dir.iterdir():
        if not variant_dir.is_dir():
            continue
        variant = variant_dir.name
        if variant not in VARIANT_ORDER:
            continue
        for p in sorted(variant_dir.glob("table_topics_*.json")):
            run = parse_run_from_filename(p)
            if run is None:
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    all_topics[variant][run] = json.load(f)
            except Exception as e:
                print(f"  AVISO: erro ao ler {p}: {e}")
    return all_topics


def load_metrics(input_dir: Path, llm_model: str):
    metrics = defaultdict(dict)
    for variant_dir in input_dir.iterdir():
        if not variant_dir.is_dir():
            continue
        variant = variant_dir.name
        if variant not in VARIANT_ORDER:
            continue
        for p in sorted(variant_dir.glob(f"metrics_{llm_model.upper()}_*.json")):
            run = parse_run_from_filename(p)
            if run is None:
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                summary = data.get("_summary", {})
                metrics[variant][run] = {
                    "tokens_in": summary.get("total_tokens_in", 0),
                }
            except Exception as e:
                print(f"  AVISO: erro ao ler métricas {p}: {e}")
    return metrics


def collect_unique_themes(all_topics_per_model: dict):
    unique = set()
    for all_topics in all_topics_per_model.values():
        for variant, runs in all_topics.items():
            for run, tables in runs.items():
                for topics in tables.values():
                    for t in safe_list(topics):
                        nt = normalize_theme(t)
                        if nt:
                            unique.add(nt)
    return sorted(unique)


def get_embeddings(texts: list, api_key: str) -> np.ndarray:
    client = OpenAI(api_key=api_key)
    embeddings = []
    print(f"Gerando embeddings para {len(texts)} temas únicos...")
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        embeddings.extend([item.embedding for item in resp.data])
        print(f"  {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")
    return np.asarray(embeddings, dtype=np.float32)


def build_embedding_lookup(unique_themes, embeddings):
    return {t: embeddings[i] for i, t in enumerate(unique_themes)}


def topics_for(all_topics, variant, run, table):
    topics = safe_list(all_topics.get(variant, {}).get(run, {}).get(table, []))
    topics = [normalize_theme(t) for t in topics]
    return sorted(set(t for t in topics if t))


def soft_dice_semantic(list_a: list, list_b: list, emb_lookup: dict) -> float:
    """Soft Dice semântico via Hungarian matching (igual ao artigo/script original)."""
    n, m = len(list_a), len(list_b)
    denom = n + m
    if denom == 0:
        return 1.0
    if n == 0 or m == 0:
        return 0.0

    list_a = [t for t in list_a if t in emb_lookup]
    list_b = [t for t in list_b if t in emb_lookup]
    if not list_a or not list_b:
        return 0.0

    A = np.vstack([emb_lookup[t] for t in list_a])
    B = np.vstack([emb_lookup[t] for t in list_b])
    S = cosine_similarity(A, B)
    cost = 1.0 - S
    row_ind, col_ind = linear_sum_assignment(cost)
    sim_sum = sum(
        float(S[i, j]) for i, j in zip(row_ind, col_ind)
        if float(S[i, j]) >= SIMILARITY_THRESHOLD
    )
    return float((2.0 * sim_sum) / denom)


# =============================================================================
# RQ6 — shift (vs full) x custo de tokens, por modelo
# =============================================================================

def compare_to_full(all_topics: dict, metrics: dict, emb_lookup: dict,
                     variant: str, all_tables: list) -> dict | None:
    """SoftDice médio de `variant` vs v01_full + tokens_in médio de `variant`."""
    runs_a = set(all_topics.get(variant, {}).keys())
    runs_b = set(all_topics.get(BASELINE_VARIANT, {}).keys())
    common_runs = sorted(runs_a & runs_b)
    if not common_runs:
        return None

    vals_soft = []
    for table in all_tables:
        for run in common_runs:
            a = topics_for(all_topics, variant, run, table)
            b = topics_for(all_topics, BASELINE_VARIANT, run, table)
            if not a and not b:
                vals_soft.append(1.0)
            else:
                vals_soft.append(soft_dice_semantic(a, b, emb_lookup))

    vm = metrics.get(variant, {})
    runs_with_metrics = [r for r in common_runs if r in vm]
    tokens_in = (
        float(np.mean([vm[r]["tokens_in"] for r in runs_with_metrics]))
        if runs_with_metrics else float("nan")
    )

    return {
        "SoftDice_vs_full": float(np.mean(vals_soft)),
        "TokensIn_mean": tokens_in,
    }


def run_rq6_for_model(llm_model: str, all_topics: dict, metrics: dict,
                       emb_lookup: dict) -> pd.DataFrame:
    all_tables = sorted(set(
        table
        for variant in all_topics.values()
        for run in variant.values()
        for table in run.keys()
    ))

    noise = INTRA_MODEL_NOISE.get(llm_model, {}).get(DATASET)
    if noise is None:
        print(f"  AVISO: sem piso de ruído para {llm_model}/{DATASET} — modelo ignorado na RQ6")
        return pd.DataFrame()

    rows = []
    for variant in VARIANT_ORDER:
        if variant == BASELINE_VARIANT:
            # full é a própria referência -> shift = 0 por definição
            vm = metrics.get(BASELINE_VARIANT, {})
            tokens_in = (
                float(np.mean([v["tokens_in"] for v in vm.values()]))
                if vm else float("nan")
            )
            rows.append({
                "LLM_Model": llm_model,
                "Configuracao": variant,
                "SoftDice_vs_full": 1.0,
                "Shift": 0.0,
                "TokensIn_mean": tokens_in,
            })
            continue

        if variant not in all_topics:
            continue

        res = compare_to_full(all_topics, metrics, emb_lookup, variant, all_tables)
        if res is None:
            continue

        shift = noise - res["SoftDice_vs_full"]
        rows.append({
            "LLM_Model": llm_model,
            "Configuracao": variant,
            "SoftDice_vs_full": res["SoftDice_vs_full"],
            "Shift": shift,
            "TokensIn_mean": res["TokensIn_mean"],
        })

    return pd.DataFrame(rows)


# =============================================================================
# PLOT
# =============================================================================

def plot_rq6(df: pd.DataFrame, out_path: Path):
    plt.style.use(PLT_STYLE)
    fig, ax = plt.subplots(figsize=(11, 7))

    ax.scatter(df["TokensIn_mean"], df["Shift_mean"], c="steelblue", zorder=5, s=80)
    for _, row in df.iterrows():
        ax.annotate(
            row["Configuracao"],
            (row["TokensIn_mean"], row["Shift_mean"]),
            fontsize=7, xytext=(5, 3), textcoords="offset points",
        )

    ax.axhline(0.0, color="red", linestyle="--", linewidth=1.2,
               label="v01_full (shift = 0, referência)")

    ax.set_xlabel("Tokens de entrada (média entre modelos)")
    ax.set_ylabel("Shift médio vs. full (η − SoftDice)")
    ax.set_title(
        f"RQ6 — Estabilidade semântica x custo de tokens ({DATASET.upper()})\n"
        f"Quanto menor o shift e menor o custo, mais eficiente a configuração",
        fontsize=10,
    )
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()
    print(f"  → {out_path.name}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    api_key = load_env()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não encontrada no .env")

    active_models = {llm: path for llm, path in LLM_MODELS.items() if path.exists()}
    if not active_models:
        raise RuntimeError("Nenhuma pasta de input encontrada. Verifique LLM_MODELS.")
    print(f"\nDataset: {DATASET}")
    print(f"Modelos encontrados: {list(active_models.keys())}")

    all_topics_per_model = {}
    all_metrics_per_model = {}
    for llm_model, input_dir in active_models.items():
        print(f"\nCarregando {llm_model}...")
        all_topics_per_model[llm_model] = load_ablation_runs(input_dir)
        all_metrics_per_model[llm_model] = load_metrics(input_dir, llm_model)

    unique_themes = collect_unique_themes(all_topics_per_model)
    emb = get_embeddings(unique_themes, api_key)
    emb_lookup = build_embedding_lookup(unique_themes, emb)

    per_model_frames = []
    for llm_model, input_dir in active_models.items():
        print(f"\n{'='*60}\n  RQ6 — {llm_model}\n{'='*60}")
        df_model = run_rq6_for_model(
            llm_model,
            all_topics_per_model[llm_model],
            all_metrics_per_model[llm_model],
            emb_lookup,
        )
        if not df_model.empty:
            per_model_frames.append(df_model)

    if not per_model_frames:
        raise RuntimeError("Nenhum resultado gerado — confira DATASET e os dados de entrada.")

    df_all = pd.concat(per_model_frames, ignore_index=True)
    df_all.to_csv(OUTPUT_DIR / f"rq6_token_cost_{DATASET}_per_model.csv", index=False)

    # Média entre os 4 modelos, por configuração (igual à convenção das RQ1-RQ5)
    df_summary = (
        df_all
        .groupby("Configuracao")
        .agg(
            Shift_mean=("Shift", "mean"),
            Shift_std=("Shift", "std"),
            TokensIn_mean=("TokensIn_mean", "mean"),
            N_Modelos=("LLM_Model", "nunique"),
        )
        .reset_index()
        .sort_values("TokensIn_mean")
    )
    df_summary.to_csv(OUTPUT_DIR / f"rq6_token_cost_{DATASET}.csv", index=False)

    print(f"\n{'='*75}\nRQ6 — {DATASET.upper()} — shift médio (vs full) x custo de tokens\n{'='*75}")
    print(df_summary.to_string(index=False))

    plot_rq6(df_summary, OUTPUT_DIR / f"rq6_token_cost_{DATASET}.png")

    print(f"\n✓ Resultados em: {OUTPUT_DIR}")
    print(f"  rq6_token_cost_{DATASET}.csv           (tabela para o artigo)")
    print(f"  rq6_token_cost_{DATASET}_per_model.csv (detalhe por modelo)")
    print(f"  rq6_token_cost_{DATASET}.png")


if __name__ == "__main__":
    main()