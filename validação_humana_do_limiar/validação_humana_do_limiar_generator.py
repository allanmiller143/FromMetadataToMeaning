import os
import json
import numpy as np
import pandas as pd
import unicodedata
import random
from pathlib import Path
from itertools import combinations, product
from collections import defaultdict
from dotenv import load_dotenv
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from scipy.optimize import linear_sum_assignment

# ======================================================
# CONFIGURAÇÕES - CAMINHOS AUTOMATIZADOS
# ======================================================
# O script agora reside em: ...\WCCI - V2\validação_humana_do_limiar\validação_humana_do_limiar_generator.py
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent

# Pastas de saída organizadas
ROTULADOS_DIR = SCRIPT_DIR / "rotulados"
GABARITO_DIR = SCRIPT_DIR / "gabarito"

ROTULADOS_DIR.mkdir(parents=True, exist_ok=True)
GABARITO_DIR.mkdir(parents=True, exist_ok=True)

BASES_PATHS = [
    PROJECT_ROOT / "data" / "magento2" / "step3_output",
    PROJECT_ROOT / "data" / "nhanes" / "step3_output",
    PROJECT_ROOT / "data" / "teixeira" / "step3_output",
]

MODELS = ["MISTRAL", "OPENAI", "DEEPSEEK", "GEMINI"]
EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100
RANDOM_SEED = 42
SIMILARITY_MIN = 0.35
SIMILARITY_MAX = 0.7
STRATIFIED_BIN_SIZE = 0.05
SAMPLES_PER_BASE = 100
PIPELINE_THRESHOLD = 0.5

# ======================================================
# UTILS
# ======================================================
def load_env():
    # Caminho absoluto para o .env na raiz do projeto
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        print(f"Aviso: Arquivo .env não encontrado em {env_path}")

    load_dotenv(env_path)
    return os.getenv("OPENAI_API_KEY")

def normalize_theme(theme: str) -> str:
    if theme is None: return ""
    theme = str(theme)
    normalized = "".join(
        c for c in unicodedata.normalize("NFD", theme)
        if unicodedata.category(c) != "Mn"
    )
    return normalized.lower().strip()

def safe_list(x):
    return x if isinstance(x, list) else []

def load_topics_from_path(path: Path):
    all_topics = defaultdict(dict)
    found_files = list(path.glob("table_topics_*.json"))
    for p in found_files:
        name = p.name
        if not name.startswith("table_topics_"): continue
        try:
            core = name.replace("table_topics_", "").replace(".json", "")
            parts = core.split("_")
            if len(parts) < 2: continue
            model = "_".join(parts[:-1])
            run = int(parts[-1])
            if model in MODELS:
                with open(p, "r", encoding="utf-8") as f:
                    all_topics[model][run] = json.load(f)
        except Exception: pass
    return all_topics

def get_embeddings_with_cache(texts, api_key, cache_path):
    if cache_path.exists():
        print(f"  Carregando embeddings do cache: {cache_path}")
        return np.load(cache_path)

    print(f"  Gerando embeddings para {len(texts)} temas...")
    client = OpenAI(api_key=api_key)
    embeddings = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        embeddings.extend([item.embedding for item in resp.data])

    arr = np.asarray(embeddings, dtype=np.float32)
    np.save(cache_path, arr)
    return arr

# ======================================================
# PROCESSAMENTO POR BASE
# ======================================================
def process_base(base_path: Path, api_key: str):
    base_name = base_path.parent.name
    print(f"\n>>> Processando Base: {base_name}")

    all_topics = load_topics_from_path(base_path)
    if not all_topics:
        print(f"  Erro: Nenhum tópico encontrado em {base_path}")
        return

    unique_themes = set()
    for model, runs in all_topics.items():
        for run, tables in runs.items():
            for topics in tables.values():
                for t in safe_list(topics):
                    nt = normalize_theme(t)
                    if nt: unique_themes.add(nt)

    sorted_themes = sorted(list(unique_themes))
    cache_path = base_path.parent / f"emb_cache_{base_name}.npy"
    embeddings = get_embeddings_with_cache(sorted_themes, api_key, cache_path)
    emb_lookup = {t: embeddings[i] for i, t in enumerate(sorted_themes)}

    all_tables = set()
    for model in all_topics.keys():
        for run in all_topics[model].keys():
            all_tables.update(all_topics[model][run].keys())
    all_tables = sorted(all_tables)

    candidates = []
    for table in all_tables:
        for m1, m2 in combinations(MODELS, 2):
            if m1 not in all_topics or m2 not in all_topics: continue
            runs_m1 = sorted(all_topics[m1].keys())
            runs_m2 = sorted(all_topics[m2].keys())
            for r1, r2 in product(runs_m1, runs_m2):
                t1_raw = [normalize_theme(t) for t in safe_list(all_topics[m1][r1].get(table, []))]
                t2_raw = [normalize_theme(t) for t in safe_list(all_topics[m2][r2].get(table, []))]

                t1_filtered = [t for t in t1_raw if t and t in emb_lookup]
                t2_filtered = [t for t in t2_raw if t and t in emb_lookup]

                if not t1_filtered or not t2_filtered: continue

                v1 = np.vstack([emb_lookup[t] for t in t1_filtered])
                v2 = np.vstack([emb_lookup[t] for t in t2_filtered])

                S = cosine_similarity(v1, v2)
                row_ind, col_ind = linear_sum_assignment(1.0 - S)

                for i, j in zip(row_ind, col_ind):
                    sim = float(S[i, j])
                    if SIMILARITY_MIN <= sim <= SIMILARITY_MAX:
                        candidates.append({
                            "tema_a": t1_filtered[i],
                            "tema_b": t2_filtered[j],
                            "sim": sim,
                            "m1": m1, "m2": m2, "r1": r1, "r2": r2, "table": table
                        })

    seen = set()
    unique_candidates = []
    for c in candidates:
        pair = tuple(sorted([c["tema_a"], c["tema_b"]]))
        if pair not in seen:
            seen.add(pair)
            unique_candidates.append(c)

    random.seed(RANDOM_SEED)
    df_cand = pd.DataFrame(unique_candidates)
    if df_cand.empty:
        print(f"  Aviso: Nenhum par no range {SIMILARITY_MIN}-{SIMILARITY_MAX} para {base_name}")
        return

    bins = np.arange(SIMILARITY_MIN, SIMILARITY_MAX + STRATIFIED_BIN_SIZE, STRATIFIED_BIN_SIZE)
    df_cand['bin'] = pd.cut(df_cand['sim'], bins=bins, include_lowest=True)

    sampled_indices = set()
    bins_list = df_cand['bin'].unique()
    target_per_bin = SAMPLES_PER_BASE // len(bins_list) if len(bins_list) > 0 else 0

    for b in bins_list:
        bin_data = df_cand[df_cand['bin'] == b]
        if len(bin_data) > 0:
            sample = bin_data.sample(n=min(len(bin_data), target_per_bin), random_state=RANDOM_SEED)
            sampled_indices.update(sample.index)

    if len(sampled_indices) < SAMPLES_PER_BASE:
        remaining_indices = df_cand.index.difference(list(sampled_indices))
        needed = SAMPLES_PER_BASE - len(sampled_indices)
        if not remaining_indices.empty:
            extra_sample = random.sample(list(remaining_indices), min(len(remaining_indices), needed))
            sampled_indices.update(extra_sample)

    final_sample_df = df_cand.loc[list(sampled_indices)]
    print(f"  Amostra final: {len(final_sample_df)} pares coletados.")

    id_map = {}
    rotulagem_rows = []

    for idx, (_, item) in enumerate(final_sample_df.iterrows(), 1):
        row_id = f"{base_name}_{idx}"
        rotulagem_rows.append({
            "id": row_id,
            "tema_a": item["tema_a"],
            "tema_b": item["tema_b"],
            "match_humano": ""
        })
        id_map[row_id] = {
            "similaridade_real": item["sim"],
            "threshold_atual_pipeline": PIPELINE_THRESHOLD,
            "modelo_a": item["m1"],
            "modelo_b": item["m2"],
            "run_a": item["r1"],
            "run_b": item["r2"],
            "tabela": item["table"]
        }

    df_rot = pd.DataFrame(rotulagem_rows)
    # Salvando na pasta 'rotulados'
    df_rot.to_csv(ROTULADOS_DIR / f"{base_name}_para_rotular.csv", index=False, encoding="utf-8-sig")
    # Salvando na pasta 'gabarito'
    with open(GABARITO_DIR / f".gabarito_{base_name}.json", "w", encoding="utf-8") as f:
        json.dump(id_map, f, indent=2, ensure_ascii=False)

def main():
    api_key = load_env()
    if not api_key:
        print("Erro: OPENAI_API_KEY não encontrada.")
        return
    for path_str in BASES_PATHS:
        path = Path(path_str)
        if not path.exists():
            print(f"Caminho não encontrado: {path_str}")
            continue
        process_base(path, api_key)
    print("\nProcesso concluído!")

if __name__ == "__main__":
    main()
