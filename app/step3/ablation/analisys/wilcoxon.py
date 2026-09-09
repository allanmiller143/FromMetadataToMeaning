"""
======================================
Análise simplificada do estudo de ablação focada em DISTÂNCIA AO RUÍDO.

METODOLOGIA:
1. Medimos o Soft Dice médio entre execuções idênticas (RUÍDO).
2. Comparamos pares de variantes (A vs B) conforme as perguntas originais.
3. Calculamos o GAP: Ruído - Soft Dice(A, B).
4. Visualizamos o impacto real sem rótulos automáticos ou bootstrap complexo.
5. [NOVO] Testamos a significância estatística de cada gap via Wilcoxon
   signed-rank (uma amostra, per-tabela vs. ruído), com correção FDR
   por pergunta de pesquisa. Resultado salvo em arquivo CSV separado.
"""

import os
import json
import numpy as np
import pandas as pd
import unicodedata
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity
from scipy.optimize import linear_sum_assignment
from scipy.stats import wilcoxon
from statsmodels.stats.multitest import multipletests
from openai import OpenAI
from dotenv import load_dotenv

# =============================================================================
# CONFIGURAÇÃO DE PASTAS (Mantida idêntica à original)
# =============================================================================

ROOT_DIR = Path(__file__).resolve().parents[4]
DATA_DIR = ROOT_DIR / "data" / "teixeira"
STEP3_DIR = DATA_DIR / "step3_output"

LLM_MODELS_PATHS = {
    "OPENAI":   STEP3_DIR / "step3_ablation_openai",
    "DEEPSEEK": STEP3_DIR / "step3_ablation_deepseek",
    "MISTRAL":  STEP3_DIR / "step3_ablation_mistral",
    "GEMINI":   STEP3_DIR / "step3_ablation_gemini",
}

OUTPUT_DIR = STEP3_DIR / "step3_ablation_results_wilcoxon"
RQ_DIR = OUTPUT_DIR / "research_questions"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RQ_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100
SIMILARITY_THRESHOLD = 0.5
PLT_STYLE = "seaborn-v0_8-muted"
DATASET = "teixeira"  # Altere para "nhanes" conforme necessário

ALPHA = 0.05

# =============================================================================
# RUÍDO INTRA-MODELO (Seu baseline de estabilidade)
# =============================================================================

INTRA_MODEL_NOISE = {
    "OPENAI":   {"teixeira": 0.939, "nhanes": 0.917},
    "DEEPSEEK": {"teixeira": 0.919, "nhanes": 0.923},
    "MISTRAL":  {"teixeira": 0.896, "nhanes": 0.875},
    "GEMINI":   {"teixeira": 0.817, "nhanes": 0.861},
}

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
    "v22_fk_nullable_sample_rows_plus_frequent", "v23_fk_nullable_sample_rows_plus_sample_values",
    "v24_full_no_numeric_stats", "v25_full_no_sample_rows",
]

# =============================================================================
# PERGUNTAS DE PESQUISA (Suas perguntas originais mantidas)
# =============================================================================

P1_PAIRS = [
    ("v02_plus_fk",            "v00_baseline", "FK vs baseline"),
    ("v03_plus_nullable",      "v00_baseline", "nullable vs baseline"),
    ("v04_plus_numeric_stats", "v00_baseline", "numeric_stats vs baseline"),
    ("v05_plus_sample_values", "v00_baseline", "sample_values vs baseline"),
    ("v06_plus_frequent_values","v00_baseline","frequent_values vs baseline"),
    ("v07_plus_sample_rows",   "v00_baseline", "sample_rows vs baseline"),
]

P2_PAIRS = [
    ("v04_plus_numeric_stats",    "v00_baseline",         "numeric_stats sozinho"),
    ("v14_nullable_plus_numeric_stats", "v03_plus_nullable", "numeric_stats + nullable vs nullable"),
    ("v01_full",                  "v24_full_no_numeric_stats", "full vs full-sem-numeric_stats"),
]

P3_PAIRS = [
    ("v07_plus_sample_rows",     "v05_plus_sample_values",  "rows vs sample_values"),
    ("v07_plus_sample_rows",     "v06_plus_frequent_values","rows vs frequent_values"),
    ("v15_sample_rows_vs_sample_values", "v07_plus_sample_rows",   "rows+sample_val vs rows"),
    ("v15_sample_rows_vs_sample_values", "v05_plus_sample_values", "rows+sample_val vs sample_val"),
    ("v16_sample_rows_vs_frequent_values","v07_plus_sample_rows",  "rows+freq_val vs rows"),
    ("v17_sample_rows_plus_both_values",  "v07_plus_sample_rows",  "rows+ambos vs rows"),
    ("v01_full",                 "v25_full_no_sample_rows",  "full vs full-sem-rows"),
]

P4_PAIRS = [
    ("v08_fk_plus_sample_values",      "v05_plus_sample_values",  "FK+sample_val vs sample_val"),
    ("v09_fk_plus_frequent_values",    "v06_plus_frequent_values","FK+freq_val vs freq_val"),
    ("v10_fk_plus_sample_and_frequent","v08_fk_plus_sample_values","FK+ambos vs FK+sample_val"),
    ("v11_fk_plus_sample_rows",        "v07_plus_sample_rows",    "FK+rows vs rows"),
    ("v02_plus_fk",                    "v00_baseline",             "FK isolado vs baseline"),
]

P5_PAIRS = [
    ("v12_nullable_plus_sample_values",  "v05_plus_sample_values",  "nullable+sample_val vs sample_val"),
    ("v13_nullable_plus_frequent_values","v06_plus_frequent_values","nullable+freq_val vs freq_val"),
    ("v14_nullable_plus_numeric_stats",  "v04_plus_numeric_stats",  "nullable+numeric_stats vs numeric_stats"),
    ("v03_plus_nullable",                "v00_baseline",             "nullable isolado vs baseline"),
]

# =============================================================================
# UTILS & PROCESSAMENTO
# =============================================================================

def normalize_theme(theme: str) -> str:
    if theme is None: return ""
    theme = str(theme)
    normalized = "".join(c for c in unicodedata.normalize("NFD", theme) if unicodedata.category(c) != "Mn")
    return normalized.lower().strip()

def safe_list(x):
    return x if isinstance(x, list) else []

def load_ablation_runs(input_dir: Path):
    all_topics = defaultdict(dict)
    if not input_dir.exists():
        return all_topics
    for variant_dir in input_dir.iterdir():
        if not variant_dir.is_dir() or variant_dir.name not in VARIANT_ORDER: continue
        variant = variant_dir.name
        for p in variant_dir.glob("table_topics_*.json"):
            try:
                run_id = int(p.stem.split("_")[-1])
                with open(p, "r", encoding="utf-8") as f:
                    all_topics[variant][run_id] = json.load(f)
            except: continue
    return all_topics

def get_embeddings(texts: list, api_key: str) -> dict:
    if not texts: return {}
    client = OpenAI(api_key=api_key)
    lookup = {}
    print(f"\n[EMBEDDINGS] Gerando para {len(texts)} temas únicos...")
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        for j, item in enumerate(resp.data):
            lookup[batch[j]] = np.array(item.embedding)
        print(f"  Progresso: {min(i + BATCH_SIZE, len(texts))}/{len(texts)}")
    return lookup

def soft_dice_semantic(list_a: list, list_b: list, emb_lookup: dict) -> float:
    n, m = len(list_a), len(list_b)
    denom = n + m
    if denom == 0: return 1.0
    if n == 0 or m == 0: return 0.0

    list_a = [t for t in list_a if t in emb_lookup]
    list_b = [t for t in list_b if t in emb_lookup]
    if not list_a or not list_b: return 0.0

    A = np.vstack([emb_lookup[t] for t in list_a])
    B = np.vstack([emb_lookup[t] for t in list_b])
    S = cosine_similarity(A, B)
    cost = 1.0 - S
    row_ind, col_ind = linear_sum_assignment(cost)
    sim_sum = sum(float(S[i, j]) for i, j in zip(row_ind, col_ind) if float(S[i, j]) >= SIMILARITY_THRESHOLD)
    return float((2.0 * sim_sum) / denom)

def wilcoxon_vs_noise(dice_scores: list, noise_ref: float):
    """
    [NOVO] Testa se a distribuição per-tabela de Soft-Dice(A,B) difere do
    ruído de referência (noise_ref), via Wilcoxon signed-rank de uma amostra
    aplicado às diferenças (dice_scores - noise_ref).
    Retorna (statistic, p_value). Casos degenerados (todas as diffs = 0,
    ou n muito pequeno) retornam p_value = 1.0 de forma segura.
    """
    diffs = np.array(dice_scores) - noise_ref
    if len(diffs) < 1 or np.all(diffs == 0):
        return np.nan, 1.0
    try:
        stat, p_value = wilcoxon(diffs)
    except ValueError:
        # ocorre p.ex. se todas as diffs forem zero após remoção de zeros
        # internos do próprio scipy, ou n insuficiente
        return np.nan, 1.0
    return stat, p_value

def analyze_model(model_name, dataset_name, emb_lookup):
    print(f"\n" + "="*80)
    print(f" ANALISANDO MODELO: {model_name} | DATASET: {dataset_name}")
    print("="*80)
    
    input_dir = LLM_MODELS_PATHS.get(model_name)
    all_topics = load_ablation_runs(input_dir)
    
    if not all_topics:
        print(f" [AVISO] Nenhum dado encontrado em {input_dir}")
        return pd.DataFrame(), pd.DataFrame()

    noise_ref = INTRA_MODEL_NOISE.get(model_name, {}).get(dataset_name, 0.9)
    print(f" [INFO] Ruído de Referência (Estabilidade): {noise_ref:.4f}")
    
    results = []
    sig_results = []  # [NOVO] linhas para o arquivo de significância
    questions = [
        ("P1", P1_PAIRS), ("P2", P2_PAIRS), ("P3", P3_PAIRS), 
        ("P4", P4_PAIRS), ("P5", P5_PAIRS)
    ]
    
    if "v01_full" in all_topics:
        p7_pairs = [(v, "v01_full", f"{v} vs Full") for v in VARIANT_ORDER if v in all_topics and v != "v01_full"]
        questions.append(("P7", p7_pairs))

    for q_id, pairs in questions:
        print(f"\n --- Processando {q_id} ---")
        q_results = []
        q_sig_results = []  # [NOVO]
        for va, vb, label in pairs:
            if va not in all_topics or vb not in all_topics: continue
            
            runs_a = set(all_topics[va].keys())
            runs_b = set(all_topics[vb].keys())
            common_runs = sorted(runs_a & runs_b)
            if not common_runs: continue
            
            all_tables = set()
            for r in common_runs: all_tables.update(all_topics[va][r].keys())
            
            dice_scores = []
            for table in all_tables:
                table_run_scores = []
                for run in common_runs:
                    topics_a = [normalize_theme(t) for t in safe_list(all_topics[va][run].get(table, []))]
                    topics_b = [normalize_theme(t) for t in safe_list(all_topics[vb][run].get(table, []))]
                    score = soft_dice_semantic(topics_a, topics_b, emb_lookup)
                    table_run_scores.append(score)
                dice_scores.append(np.mean(table_run_scores))
            
            avg_dice = np.mean(dice_scores)
            gap = noise_ref - avg_dice
            gap_pct = (gap / noise_ref) * 100
            
            # --- Saída ORIGINAL, sem alterações ---
            res_row = {
                "Pergunta": q_id,
                "Comparacao": label,
                "SoftDice": avg_dice,
                "Impacto": gap,
                "Impacto_%": gap_pct
            }
            q_results.append(res_row)
            results.append({**res_row, "Variante_A": va, "Variante_B": vb, "Ruido": noise_ref})

            # --- [NOVO] Teste de significância, guardado à parte ---
            stat, p_value = wilcoxon_vs_noise(dice_scores, noise_ref)
            sig_row = {
                "Pergunta": q_id,
                "Comparacao": label,
                "Variante_A": va,
                "Variante_B": vb,
                "SoftDice": avg_dice,
                "Impacto": gap,
                "N_Tabelas": len(dice_scores),
                "Wilcoxon_stat": stat,
                "p_value": p_value,
            }
            q_sig_results.append(sig_row)

        # Imprime tabela da pergunta no terminal (ORIGINAL, sem alterações)
        if q_results:
            df_q = pd.DataFrame(q_results)
            print(df_q[["Comparacao", "SoftDice", "Impacto", "Impacto_%"]].to_string(index=False, float_format=lambda x: f"{x:.4f}"))

        # --- [NOVO] Correção FDR dentro da pergunta, e acumula para o modelo ---
        if q_sig_results:
            df_sig_q = pd.DataFrame(q_sig_results)
            reject, p_adj, _, _ = multipletests(df_sig_q["p_value"], method="fdr_bh", alpha=ALPHA)
            df_sig_q["p_adj_fdr"] = p_adj
            df_sig_q["significant"] = reject
            sig_results.extend(df_sig_q.to_dict("records"))

    return pd.DataFrame(results), pd.DataFrame(sig_results)

def plot_impact(df, model_name, dataset_name):
    if df.empty: return
    for q_id in df["Pergunta"].unique():
        sub = df[df["Pergunta"] == q_id].sort_values("Impacto", ascending=True)
        plt.figure(figsize=(12, 6))
        bars = plt.barh(sub["Comparacao"], sub["Impacto"], color='lightcoral')
        for bar in bars:
            width = bar.get_width()
            plt.text(width, bar.get_y() + bar.get_height()/2, f' {width:.3f}', va='center', ha='left', fontsize=10, fontweight='bold')
        plt.axvline(0, color='black', linewidth=1)
        plt.title(f"{q_id} - Impacto (Queda no Soft Dice) | {model_name} | {dataset_name}\n(Valores positivos = Queda na estabilidade em relação ao ruído)")
        plt.xlabel("Impacto Absoluto (Ruído - Soft Dice)")
        plt.tight_layout()
        plt.savefig(RQ_DIR / f"{q_id.lower()}_{model_name}_{dataset_name}.png")
        plt.close()

if __name__ == "__main__":
    load_dotenv(ROOT_DIR / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    
    all_model_results = []
    all_model_sig_results = []  # [NOVO]
    all_themes = set()
    
    print("\n[1/3] Coletando temas para embeddings...")
    for model, path in LLM_MODELS_PATHS.items():
        topics = load_ablation_runs(path)
        for variant in topics.values():
            for run in variant.values():
                for table_topics in run.values():
                    for t in safe_list(table_topics):
                        nt = normalize_theme(t)
                        if nt: all_themes.add(nt)
    
    emb_lookup = get_embeddings(sorted(list(all_themes)), api_key)
    
    print("\n[2/3] Iniciando Análise de Ablação...")
    for model in LLM_MODELS_PATHS.keys():
        df_res, df_sig = analyze_model(model, DATASET, emb_lookup)
        if not df_res.empty:
            df_res["Modelo"] = model
            all_model_results.append(df_res)
            plot_impact(df_res, model, DATASET)
        if not df_sig.empty:
            df_sig["Modelo"] = model
            all_model_sig_results.append(df_sig)
    
    print("\n[3/3] Finalizando e salvando resultados...")
    if all_model_results:
        # --- Saída ORIGINAL, exatamente como antes ---
        final_df = pd.concat(all_model_results)
        csv_path = OUTPUT_DIR / "resultado_ablacao_impacto_esus.csv"
        final_df.to_csv(csv_path, index=False, sep=";", decimal=",")
        print(f"\n" + "!"*80)
        print(f" SUCESSO! ")
        print(f" Tabela consolidada: {csv_path}")
        print(f" Gráficos gerados em: {RQ_DIR}")
        print("!"*80)
    else:
        print("\n[ERRO] Nenhum dado foi processado. Verifique os caminhos e arquivos JSON.")

    if all_model_sig_results:
        final_sig_df = pd.concat(all_model_sig_results)
        sig_csv_path = OUTPUT_DIR / "resultado_ablacao_significancia_esus.csv"
        final_sig_df.to_csv(sig_csv_path, index=False, sep=";", decimal=",")
        print(f"\n" + "#"*80)
        print(f" TESTES DE SIGNIFICÂNCIA (Wilcoxon signed-rank vs. ruído, FDR por pergunta)")
        print(f" Arquivo: {sig_csv_path}")
        print("#"*80)
    else:
        print("\n[AVISO] Nenhum resultado de significância foi gerado.")