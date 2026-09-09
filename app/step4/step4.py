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
DATA_DIR = ROOT_DIR / "data" / "nhanes"
INPUT_DIR = DATA_DIR / "step3_output"
OUTPUT_DIR = DATA_DIR / "step4_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODELS = ["MISTRAL", "OPENAI", "DEEPSEEK", "GEMINI"]

EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100

MAKE_PLOTS = True
PLT_STYLE = "seaborn-v0_8-darkgrid"

# se quiser salvar auditoria detalhada dos pareamentos
SAVE_PAIR_AUDIT = True

SIMILARITY_THRESHOLD = 0.5


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
                print(f"AVISO: arquivo ignorado por run não numérico: {name}")
                continue

            run = int(run_str)

            if model not in MODELS:
                print(f"AVISO: modelo fora de MODELS, pulando: {name} (model={model})")
                continue

            with open(p, "r", encoding="utf-8") as f:
                all_topics[model][run] = json.load(f)

        except Exception as e:
            print(f"AVISO: erro ao ler {p}: {e}")

    print("\nResumo dos arquivos carregados (modelo -> runs):")
    for model in sorted(all_topics.keys()):
        runs = sorted(all_topics[model].keys())
        print(f"  {model} -> {runs}")

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
    client = OpenAI(api_key=api_key)
    embeddings = []
    print(f"Gerando embeddings para {len(texts)} temas únicos...")

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        resp = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch
        )
        embeddings.extend([item.embedding for item in resp.data])
        print(f"Processados: {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")

    return np.asarray(embeddings, dtype=np.float32)


def build_embedding_lookup(unique_themes, embeddings):
    return {t: embeddings[i] for i, t in enumerate(unique_themes)}


def topics_for(all_topics, model, run, table):
    topics = safe_list(all_topics.get(model, {}).get(run, {}).get(table, []))
    topics = [normalize_theme(t) for t in topics]
    topics = [t for t in topics if t]
    return sorted(set(topics))


# =========================
# HARD DICE (LEXICAL)
# =========================
def dice_lexical(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    return float((2.0 * inter) / (len(set_a) + len(set_b)))


# =========================
# SOFT DICE (SEMANTIC) + PAIRS
# =========================
def soft_dice_semantic_with_pairs(list_a: list[str], list_b: list[str], emb_lookup: dict):
    n, m = len(list_a), len(list_b)
    denom = n + m

    if denom == 0:
        return 1.0, []
    if n == 0 or m == 0:
        return 0.0, []

    list_a = [t for t in list_a if t in emb_lookup]
    list_b = [t for t in list_b if t in emb_lookup]

    if not list_a or not list_b:
        return 0.0, []

    A = np.vstack([emb_lookup[t] for t in list_a])
    B = np.vstack([emb_lookup[t] for t in list_b])

    S = cosine_similarity(A, B)
    cost = 1.0 - S

    row_ind, col_ind = linear_sum_assignment(cost)

    pairs = []
    sim_sum = 0.0

    for i, j in zip(row_ind, col_ind):
        sim = float(S[i, j])
        matched = sim >= SIMILARITY_THRESHOLD
        if matched:
            sim_sum += sim
        pairs.append({
            "tema_a": list_a[i],
            "tema_b": list_b[j],
            "similarity": sim,
            "matched": matched,
        })

    soft = float((2.0 * sim_sum) / denom)
    return soft, pairs


def soft_dice_semantic(list_a: list[str], list_b: list[str], emb_lookup: dict) -> float:
    soft, _ = soft_dice_semantic_with_pairs(list_a, list_b, emb_lookup)
    return soft


# =========================
# MAIN ANALYSIS
# =========================
def main():
    api_key = load_env()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não encontrada no .env")

    all_topics = load_all_topics_all_runs()

    detected_models = sorted(all_topics.keys())
    if not detected_models:
        raise RuntimeError("Nenhum arquivo table_topics_*.json encontrado.")

    detected_runs = sorted({run for runs in all_topics.values() for run in runs.keys()})

    all_tables = set()
    for model in all_topics.keys():
        for run in all_topics[model].keys():
            all_tables.update(all_topics[model][run].keys())
    all_tables = sorted(all_tables)

    unique_themes = collect_unique_themes(all_topics)
    emb = get_embeddings(unique_themes, api_key)
    emb_lookup = build_embedding_lookup(unique_themes, emb)

    intra_rows = []
    inter_rows = []

    pair_audit = {
        "meta": {
            "embedding_model": EMBEDDING_MODEL,
            "models_detected": detected_models,
            "runs_detected": detected_runs,
            "n_tables": len(all_tables),
            "n_unique_themes": len(unique_themes),
        },
        "intra": defaultdict(list),
        "inter": defaultdict(list),
    }

    # =========================
    # INTRA
    # =========================
    for table in all_tables:
        for model in detected_models:
            run_list = sorted(all_topics[model].keys())
            if len(run_list) < 2:
                continue

            run_pairs = list(combinations(run_list, 2))
            vals_hard = []
            vals_soft = []

            for r1, r2 in run_pairs:
                a = topics_for(all_topics, model, r1, table)
                b = topics_for(all_topics, model, r2, table)

                if not a and not b:
                    hard = 1.0
                    soft = 1.0
                    pairs = []
                else:
                    hard = dice_lexical(set(a), set(b))
                    soft, pairs = soft_dice_semantic_with_pairs(a, b, emb_lookup)

                vals_hard.append(hard)
                vals_soft.append(soft)

                if SAVE_PAIR_AUDIT:
                    pair_audit["intra"][table].append({
                        "model": model,
                        "run_a": r1,
                        "run_b": r2,
                        "n_topics_a": len(a),
                        "n_topics_b": len(b),
                        "hard_dice": hard,
                        "soft_dice": soft,
                        "pairs": pairs
                    })

            intra_rows.append({
                "Tabela": table,
                "Modelo": model,
                "HardDice_Lex_mean": float(np.mean(vals_hard)) if vals_hard else 0.0,
                "SoftDice_Sem_mean": float(np.mean(vals_soft)) if vals_soft else 0.0,
            })

    df_intra = pd.DataFrame(intra_rows)
    df_intra.to_csv(OUTPUT_DIR / "intra_consistency.csv", index=False)

    # =========================
    # INTER
    # =========================
    for table in all_tables:
        for m1, m2 in combinations(detected_models, 2):
            runs_m1 = sorted(all_topics[m1].keys())
            runs_m2 = sorted(all_topics[m2].keys())

            vals_hard = []
            vals_soft = []

            for r1, r2 in product(runs_m1, runs_m2):
                a = topics_for(all_topics, m1, r1, table)
                b = topics_for(all_topics, m2, r2, table)

                if not a and not b:
                    hard = 1.0
                    soft = 1.0
                    pairs = []
                else:
                    hard = dice_lexical(set(a), set(b))
                    soft, pairs = soft_dice_semantic_with_pairs(a, b, emb_lookup)

                vals_hard.append(hard)
                vals_soft.append(soft)

                if SAVE_PAIR_AUDIT:
                    pair_audit["inter"][table].append({
                        "model_a": m1,
                        "run_a": r1,
                        "model_b": m2,
                        "run_b": r2,
                        "n_topics_a": len(a),
                        "n_topics_b": len(b),
                        "hard_dice": hard,
                        "soft_dice": soft,
                        "pairs": pairs
                    })

            inter_rows.append({
                "Tabela": table,
                "ModelPair": f"{m1}__VS__{m2}",
                "HardDice_Lex_mean": float(np.mean(vals_hard)) if vals_hard else 0.0,
                "SoftDice_Sem_mean": float(np.mean(vals_soft)) if vals_soft else 0.0,
            })

    df_inter = pd.DataFrame(inter_rows)
    df_inter.to_csv(OUTPUT_DIR / "inter_consistency.csv", index=False)

    # =========================
    # SUMMARY
    # =========================
    summary = []

    for model in detected_models:
        d = df_intra[df_intra["Modelo"] == model]
        if d.empty:
            continue

        summary.append({
            "Tipo": "INTRA",
            "Alvo": model,
            "HardDice_Lex_mean": float(d["HardDice_Lex_mean"].mean()),
            "SoftDice_Sem_mean": float(d["SoftDice_Sem_mean"].mean()),
            "N_Tabelas": int(d.shape[0]),
        })

    for m1, m2 in combinations(detected_models, 2):
        mp = f"{m1}__VS__{m2}"
        d = df_inter[df_inter["ModelPair"] == mp]
        if d.empty:
            continue

        summary.append({
            "Tipo": "INTER",
            "Alvo": mp,
            "HardDice_Lex_mean": float(d["HardDice_Lex_mean"].mean()),
            "SoftDice_Sem_mean": float(d["SoftDice_Sem_mean"].mean()),
            "N_Tabelas": int(d.shape[0]),
        })

    df_summary = pd.DataFrame(summary)
    df_summary.to_csv(OUTPUT_DIR / "summary_consistency.csv", index=False)

    # =========================
    # AUDIT JSON
    # =========================
    if SAVE_PAIR_AUDIT:
        pair_audit["intra"] = dict(pair_audit["intra"])
        pair_audit["inter"] = dict(pair_audit["inter"])

        with open(OUTPUT_DIR / "semantic_pair_audit.json", "w", encoding="utf-8") as f:
            json.dump(pair_audit, f, ensure_ascii=False, indent=2)

        # opcional: formato tabular para facilitar filtros
        flat_rows = []

        for table, entries in pair_audit["intra"].items():
            for item in entries:
                for p in item["pairs"]:
                    flat_rows.append({
                        "Tipo": "INTRA",
                        "Tabela": table,
                        "ModelA": item["model"],
                        "RunA": item["run_a"],
                        "ModelB": item["model"],
                        "RunB": item["run_b"],
                        "HardDice": item["hard_dice"],
                        "SoftDice": item["soft_dice"],
                        "TemaA": p["tema_a"],
                        "TemaB": p["tema_b"],
                        "Similarity": p["similarity"],
                    })

        for table, entries in pair_audit["inter"].items():
            for item in entries:
                for p in item["pairs"]:
                    flat_rows.append({
                        "Tipo": "INTER",
                        "Tabela": table,
                        "ModelA": item["model_a"],
                        "RunA": item["run_a"],
                        "ModelB": item["model_b"],
                        "RunB": item["run_b"],
                        "HardDice": item["hard_dice"],
                        "SoftDice": item["soft_dice"],
                        "TemaA": p["tema_a"],
                        "TemaB": p["tema_b"],
                        "Similarity": p["similarity"],
                    })

        df_pairs = pd.DataFrame(flat_rows)
        df_pairs.to_csv(OUTPUT_DIR / "semantic_pairs_flat.csv", index=False)

    # =========================
    # PLOTS
    # =========================
    if MAKE_PLOTS:
        plt.style.use(PLT_STYLE)

        w = 0.35

        intra_bar = df_summary[df_summary["Tipo"] == "INTRA"].copy()
        if not intra_bar.empty:
            x = np.arange(len(intra_bar))
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(x - w/2, intra_bar["HardDice_Lex_mean"], width=w, label="HardDice (léxico)")
            ax.bar(x + w/2, intra_bar["SoftDice_Sem_mean"], width=w, label="SoftDice (semântico)")
            ax.set_xticks(x)
            ax.set_xticklabels(intra_bar["Alvo"], rotation=0)
            ax.set_ylim(0, 1.02)
            ax.set_title("Consistência INTRA (por modelo)")
            ax.set_ylabel("Dice médio")
            ax.legend()
            plt.tight_layout()
            plt.savefig(OUTPUT_DIR / "dice_bar_intra.png", dpi=200)
            plt.close()

        inter_bar = df_summary[df_summary["Tipo"] == "INTER"].copy()
        if not inter_bar.empty:
            x = np.arange(len(inter_bar))
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(x - w/2, inter_bar["HardDice_Lex_mean"], width=w, label="HardDice (léxico)")
            ax.bar(x + w/2, inter_bar["SoftDice_Sem_mean"], width=w, label="SoftDice (semântico)")
            ax.set_xticks(x)
            ax.set_xticklabels(inter_bar["Alvo"], rotation=15, ha="right")
            ax.set_ylim(0, 1.02)
            ax.set_title("Consistência INTER (por par de modelos)")
            ax.set_ylabel("Dice médio")
            ax.legend()
            plt.tight_layout()
            plt.savefig(OUTPUT_DIR / "dice_bar_inter.png", dpi=200)
            plt.close()

        fig, ax = plt.subplots(figsize=(10, 5))
        if not df_intra.empty:
            ax.hist(df_intra["HardDice_Lex_mean"], bins=30, alpha=0.6, label="HardDice INTRA")
            ax.hist(df_intra["SoftDice_Sem_mean"], bins=30, alpha=0.6, label="SoftDice INTRA")
        ax.set_title("Distribuição INTRA (por tabela)")
        ax.set_xlabel("Dice")
        ax.set_ylabel("N tabelas")
        ax.legend()
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / "dice_hist_intra.png", dpi=200)
        plt.close()

        fig, ax = plt.subplots(figsize=(10, 5))
        if not df_inter.empty:
            ax.hist(df_inter["HardDice_Lex_mean"], bins=30, alpha=0.6, label="HardDice INTER")
            ax.hist(df_inter["SoftDice_Sem_mean"], bins=30, alpha=0.6, label="SoftDice INTER")
        ax.set_title("Distribuição INTER (por tabela)")
        ax.set_xlabel("Dice")
        ax.set_ylabel("N tabelas")
        ax.legend()
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / "dice_hist_inter.png", dpi=200)
        plt.close()


if __name__ == "__main__":
    main()