"""
ablation_analysis.py
====================
Análise estruturada do estudo de ablação.

Responde às perguntas de pesquisa via comparações DIRECIONADAS entre pares de
variantes — não só vs v01_full.

PERGUNTAS RESPONDIDAS
─────────────────────
P1  Qual o efeito ISOLADO de cada campo? (Grupo 1 vs v00_baseline)
P2  Numeric_stats ajuda? (isolado e em contexto rico)
P3  Sample_rows vs valores por coluna — qual é mais informativo?
P4  FK acrescenta quando já há dados de valor?
P5  Nullable acrescenta quando já há dados de valor?
P6  Qual combinação intermediária chega mais perto do full com menos tokens?
P7  Comparação geral: todas as variantes vs v01_full (análise original)

Saídas geradas (em OUTPUT_DIR):
  research_questions/
    p1_isolated_effects.csv / .png
    p2_numeric_stats.csv / .png
    p3_sample_rows_vs_col_values.csv / .png
    p4_fk_interaction.csv / .png
    p5_nullable_interaction.csv / .png
    p6_efficiency_frontier.csv / .png
    p7_vs_full.csv / .png  (mantém compatibilidade com script original)
  all_pairwise_raw.csv   ← todas as comparações brutas
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
import matplotlib.ticker as mticker

# =============================================================================
# CONFIG
# =============================================================================

ROOT_DIR = Path(__file__).resolve().parents[4]
DATA_DIR = ROOT_DIR / "data/" / "teixeira"
STEP3_DIR = DATA_DIR / "step3_output"

LLM_MODELS = {
    "OPENAI":   STEP3_DIR / "step3_ablation_openai",
    "DEEPSEEK": STEP3_DIR / "step3_ablation_deepseek",
    "MISTRAL":  STEP3_DIR / "step3_ablation_mistral",
    "GEMINI":   STEP3_DIR / "step3_ablation_gemini",
}

OUTPUT_DIR = STEP3_DIR / "step3_ablation_results"
RQ_DIR = OUTPUT_DIR / "research_questions"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
RQ_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100
SIMILARITY_THRESHOLD = 0.5
PLT_STYLE = "seaborn-v0_8-darkgrid"

# =============================================================================
# RUÍDO INTRA-MODELO (variância natural entre execuções do mesmo modelo)
# Medido empiricamente rodando cada modelo 3x com os MESMOS metadados completos.
#
# Fonte ESUS  (885 tabelas): OPENAI=0.939, DEEPSEEK=0.919, MISTRAL=0.896
# Fonte NHANES (127 tabelas): OPENAI=0.917, DEEPSEEK=0.923, GEMINI=0.861, MISTRAL=0.875
#
# Interpretação: se SoftDice(A vs B) ≈ INTRA_NOISE, a diferença entre A e B
# está dentro do ruído do próprio modelo — ou seja, o campo extra NÃO importa.
#
# LIMIARES DE SIGNIFICÂNCIA (conservadores, usados na interpretação):
#   > NOISE_FLOOR       → dentro do ruído         → campo IRRELEVANTE
#   SIGNAL_WEAK .. NOISE_FLOOR → sinal fraco       → campo com IMPACTO LEVE
#   < SIGNAL_WEAK       → claramente abaixo do ruído → campo com IMPACTO REAL
#
# O NOISE_FLOOR é definido como o menor valor intra-modelo observado (0.861 —
# Gemini no NHANES), o que é conservador: qualquer diferença abaixo disso é
# sinal real mesmo no modelo mais variável.
# =============================================================================

INTRA_MODEL_NOISE = {
    # SoftDice médio intra-modelo por base (média dos modelos disponíveis)
    "OPENAI":   {"esus": 0.939, "nhanes": 0.917},
    "DEEPSEEK": {"esus": 0.919, "nhanes": 0.923},
    "MISTRAL":  {"esus": 0.896, "nhanes": 0.875},
    "GEMINI":   {"nhanes": 0.861},
}

# Piso de ruído global (mais conservador = menor valor observado)
NOISE_FLOOR   = 0.861   # Gemini/NHANES — qualquer SoftDice acima disso é ruído
SIGNAL_WEAK   = 0.800   # sinal fraco mas real
SIGNAL_STRONG = 0.700   # sinal forte e consistente

VARIANT_ORDER = [
    "v00_baseline",
    "v01_full",
    "v02_plus_fk",
    "v03_plus_nullable",
    "v04_plus_numeric_stats",
    "v05_plus_sample_values",
    "v06_plus_frequent_values",
    "v07_plus_sample_rows",
    "v08_fk_plus_sample_values",
    "v09_fk_plus_frequent_values",
    "v10_fk_plus_sample_and_frequent",
    "v11_fk_plus_sample_rows",
    "v12_nullable_plus_sample_values",
    "v13_nullable_plus_frequent_values",
    "v14_nullable_plus_numeric_stats",
    "v15_sample_rows_vs_sample_values",
    "v16_sample_rows_vs_frequent_values",
    "v17_sample_rows_plus_both_values",
    "v18_fk_nullable_sample_values",
    "v19_fk_nullable_frequent_values",
    "v20_fk_nullable_both_values",
    "v21_fk_nullable_sample_rows",
    "v22_fk_nullable_sample_rows_plus_frequent",
    "v23_fk_nullable_sample_rows_plus_sample_values",
    "v24_full_no_numeric_stats",
    "v25_full_no_sample_rows",
]

# =============================================================================
# COMPARAÇÕES DIRIGIDAS POR PERGUNTA DE PESQUISA
#
# Cada entrada é (variante_A, variante_B, label_da_comparação)
# A interpretação é sempre: "A vs B — o que A acrescenta sobre B?"
# Quando A > B em SoftDice (vs referência comum) → A melhora B.
# =============================================================================

# P1 — Efeito isolado de cada dimensão (cada uma vs baseline mínimo)
P1_PAIRS = [
    ("v02_plus_fk",            "v00_baseline", "FK vs baseline"),
    ("v03_plus_nullable",      "v00_baseline", "nullable vs baseline"),
    ("v04_plus_numeric_stats", "v00_baseline", "numeric_stats vs baseline"),
    ("v05_plus_sample_values", "v00_baseline", "sample_values vs baseline"),
    ("v06_plus_frequent_values","v00_baseline","frequent_values vs baseline"),
    ("v07_plus_sample_rows",   "v00_baseline", "sample_rows vs baseline"),
]

# P2 — Numeric_stats ajuda? (isolado + em contexto rico)
P2_PAIRS = [
    ("v04_plus_numeric_stats",    "v00_baseline",         "numeric_stats sozinho"),
    ("v14_nullable_plus_numeric_stats", "v03_plus_nullable", "numeric_stats + nullable vs nullable"),
    ("v01_full",                  "v24_full_no_numeric_stats", "full vs full-sem-numeric_stats"),
]

# P3 — Sample_rows vs valores por coluna
P3_PAIRS = [
    ("v07_plus_sample_rows",     "v05_plus_sample_values",  "rows vs sample_values"),
    ("v07_plus_sample_rows",     "v06_plus_frequent_values","rows vs frequent_values"),
    ("v15_sample_rows_vs_sample_values", "v07_plus_sample_rows",   "rows+sample_val vs rows"),
    ("v15_sample_rows_vs_sample_values", "v05_plus_sample_values", "rows+sample_val vs sample_val"),
    ("v16_sample_rows_vs_frequent_values","v07_plus_sample_rows",  "rows+freq_val vs rows"),
    ("v17_sample_rows_plus_both_values",  "v07_plus_sample_rows",  "rows+ambos vs rows"),
    ("v01_full",                 "v25_full_no_sample_rows",  "full vs full-sem-rows"),
]

# P4 — FK acrescenta quando já há dados de valor?
P4_PAIRS = [
    ("v08_fk_plus_sample_values",      "v05_plus_sample_values",  "FK+sample_val vs sample_val"),
    ("v09_fk_plus_frequent_values",    "v06_plus_frequent_values","FK+freq_val vs freq_val"),
    ("v10_fk_plus_sample_and_frequent","v08_fk_plus_sample_values","FK+ambos vs FK+sample_val"),
    ("v11_fk_plus_sample_rows",        "v07_plus_sample_rows",    "FK+rows vs rows"),
    ("v02_plus_fk",                    "v00_baseline",             "FK isolado vs baseline"),
]

# P5 — Nullable acrescenta quando já há dados de valor?
P5_PAIRS = [
    ("v12_nullable_plus_sample_values",  "v05_plus_sample_values",  "nullable+sample_val vs sample_val"),
    ("v13_nullable_plus_frequent_values","v06_plus_frequent_values","nullable+freq_val vs freq_val"),
    ("v14_nullable_plus_numeric_stats",  "v04_plus_numeric_stats",  "nullable+numeric_stats vs numeric_stats"),
    ("v03_plus_nullable",                "v00_baseline",             "nullable isolado vs baseline"),
]

# P6 — Fronteira de eficiência (qualidade / tokens)
# Todas as variantes são analisadas juntas; só selecionamos as "candidatas a ótimo"
P6_CANDIDATES = [
    "v00_baseline",
    "v05_plus_sample_values",
    "v06_plus_frequent_values",
    "v07_plus_sample_rows",
    "v18_fk_nullable_sample_values",
    "v19_fk_nullable_frequent_values",
    "v20_fk_nullable_both_values",
    "v21_fk_nullable_sample_rows",
    "v22_fk_nullable_sample_rows_plus_frequent",
    "v23_fk_nullable_sample_rows_plus_sample_values",
    "v24_full_no_numeric_stats",
    "v25_full_no_sample_rows",
    "v01_full",
]

# P7 — Todas vs v01_full (análise original / compatibilidade)
BASELINE_VARIANT = "v01_full"

# =============================================================================
# UTILS
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
                    "tokens_in":    summary.get("total_tokens_in", 0),
                    "tokens_out":   summary.get("total_tokens_out", 0),
                    "tokens_total": summary.get("total_tokens", 0),
                    "elapsed_s":    summary.get("total_elapsed_s", 0.0),
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


# =============================================================================
# MÉTRICAS DE SIMILARIDADE
# =============================================================================

def dice_lexical(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a & set_b)
    return float((2.0 * inter) / (len(set_a) + len(set_b)))


def soft_dice_semantic(list_a: list, list_b: list, emb_lookup: dict) -> float:
    """Soft Dice semântico via Hungarian matching."""
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
# COMPARAÇÃO DE UM PAR DE VARIANTES (A vs B) — retorna linha de resultado
# =============================================================================

def compare_pair(
    llm_model: str,
    all_topics: dict,
    metrics: dict,
    emb_lookup: dict,
    variant_a: str,
    variant_b: str,
    comparison_label: str,
    all_tables: list,
) -> list[dict]:
    """
    Compara variant_a contra variant_b tabela a tabela.

    A métrica SoftDice aqui NÃO é vs um baseline externo — ela mede a
    SOBREPOSIÇÃO semântica entre os tópicos que A gerou vs os que B gerou.

    Quando A tem mais tópicos relevantes do que B → A > B → campo de A importa.
    Como A e B são sempre comparados com o mesmo conjunto de runs, a diferença
    é atribuível às features adicionais de A sobre B.
    """
    runs_a = set(all_topics.get(variant_a, {}).keys())
    runs_b = set(all_topics.get(variant_b, {}).keys())
    common_runs = sorted(runs_a & runs_b)

    if not common_runs:
        print(f"  AVISO: sem runs em comum entre {variant_a} e {variant_b} — pulando")
        return []

    rows = []
    for table in all_tables:
        vals_hard, vals_soft = [], []
        for run in common_runs:
            a = topics_for(all_topics, variant_a, run, table)
            b = topics_for(all_topics, variant_b, run, table)
            if not a and not b:
                vals_hard.append(1.0)
                vals_soft.append(1.0)
            else:
                vals_hard.append(dice_lexical(set(a), set(b)))
                vals_soft.append(soft_dice_semantic(a, b, emb_lookup))

        # Tokens médios de A e de B separadamente
        def avg_tokens_in(variant):
            vm = metrics.get(variant, {})
            runs_with = [r for r in common_runs if r in vm]
            if not runs_with:
                return float("nan")
            return float(np.mean([vm[r]["tokens_in"] for r in runs_with]))

        rows.append({
            "LLM_Model":         llm_model,
            "Tabela":            table,
            "Variante_A":        variant_a,
            "Variante_B":        variant_b,
            "Comparacao":        comparison_label,
            "Runs_Comparados":   len(common_runs),
            "HardDice_mean":     float(np.mean(vals_hard)),
            "SoftDice_mean":     float(np.mean(vals_soft)),
            "TokensIn_A_mean":   avg_tokens_in(variant_a),
            "TokensIn_B_mean":   avg_tokens_in(variant_b),
            # Delta de tokens: custo extra de A sobre B
            "Delta_TokensIn":    avg_tokens_in(variant_a) - avg_tokens_in(variant_b),
        })

    return rows


# =============================================================================
# ANÁLISE POR PERGUNTA DE PESQUISA
# =============================================================================

def summarize_pairs(df_raw: pd.DataFrame, group_col: str = "Comparacao") -> pd.DataFrame:
    """Agrega por comparação (média de todas as tabelas e modelos)."""
    agg = (
        df_raw
        .groupby([group_col, "Variante_A", "Variante_B"])
        .agg(
            N_Tabelas=("Tabela", "count"),
            HardDice_mean=("HardDice_mean", "mean"),
            SoftDice_mean=("SoftDice_mean", "mean"),
            SoftDice_std=("SoftDice_mean", "std"),
            TokensIn_A=("TokensIn_A_mean", "mean"),
            TokensIn_B=("TokensIn_B_mean", "mean"),
            Delta_TokensIn=("Delta_TokensIn", "mean"),
        )
        .reset_index()
    )
    return agg.sort_values("SoftDice_mean", ascending=False)


def run_research_questions(llm_model: str, all_topics: dict, metrics: dict,
                           emb_lookup: dict) -> pd.DataFrame:
    """
    Roda todas as comparações dirigidas para um modelo.
    Retorna um DataFrame 'raw' com uma linha por (comparação, tabela).
    """
    all_tables = sorted(set(
        table
        for variant in all_topics.values()
        for run in variant.values()
        for table in run.keys()
    ))

    all_rows = []

    def run_pairs(pairs, rq_label):
        for va, vb, label in pairs:
            if va not in all_topics or vb not in all_topics:
                print(f"  AVISO [{rq_label}]: variante ausente — {va} ou {vb}")
                continue
            rows = compare_pair(
                llm_model, all_topics, metrics, emb_lookup,
                va, vb, label, all_tables,
            )
            for r in rows:
                r["RQ"] = rq_label
            all_rows.extend(rows)

    # P7 é "todas vs v01_full" — gera automaticamente
    p7_pairs = [
        (v, BASELINE_VARIANT, f"{v} vs {BASELINE_VARIANT}")
        for v in VARIANT_ORDER
        if v != BASELINE_VARIANT and v in all_topics
    ]

    run_pairs(P1_PAIRS, "P1_isolated_effects")
    run_pairs(P2_PAIRS, "P2_numeric_stats")
    run_pairs(P3_PAIRS, "P3_sample_rows_vs_col_values")
    run_pairs(P4_PAIRS, "P4_fk_interaction")
    run_pairs(P5_PAIRS, "P5_nullable_interaction")
    run_pairs(p7_pairs, "P7_vs_full")

    return pd.DataFrame(all_rows)


# =============================================================================
# FRONTEIRA DE EFICIÊNCIA (P6) — qualidade vs tokens para cada variante
# =============================================================================

def build_efficiency_df(df_p7_raw: pd.DataFrame, metrics: dict, llm_model: str) -> pd.DataFrame:
    """
    Para P6 queremos: (variante, SoftDice_vs_full, tokens_entrada_media).
    Usamos as comparações P7 (variante vs v01_full) como proxy de 'qualidade'
    e os tokens de entrada da variante como 'custo'.

    Também inclui v01_full (qualidade = 1.0 por definição, custo = tokens_full).
    """
    rows_p7 = df_p7_raw[df_p7_raw["RQ"] == "P7_vs_full"]

    summary = (
        rows_p7
        .groupby("Variante_A")
        .agg(
            SoftDice_vs_full=("SoftDice_mean", "mean"),
            TokensIn_mean=("TokensIn_A_mean", "mean"),
        )
        .reset_index()
        .rename(columns={"Variante_A": "Variante"})
    )

    # Adiciona v01_full com qualidade 1.0
    vm = metrics.get(BASELINE_VARIANT, {})
    if vm:
        toks_full = float(np.mean([v["tokens_in"] for v in vm.values()]))
        full_row = pd.DataFrame([{
            "Variante": BASELINE_VARIANT,
            "SoftDice_vs_full": 1.0,
            "TokensIn_mean": toks_full,
        }])
        summary = pd.concat([summary, full_row], ignore_index=True)

    summary["LLM_Model"] = llm_model
    summary["Tokens_per_Quality"] = (
        summary["TokensIn_mean"] / summary["SoftDice_vs_full"].replace(0, np.nan)
    )
    return summary.sort_values("SoftDice_vs_full", ascending=False)


# =============================================================================
# PLOTS
# =============================================================================

def _bar_horizontal(df: pd.DataFrame, x_col: str, y_col: str, title: str,
                    xlabel: str, out_path: Path, color="steelblue",
                    vline: float = None, highlight: str = None):
    plt.style.use(PLT_STYLE)
    fig, ax = plt.subplots(figsize=(10, max(4, len(df) * 0.45)))
    colors = [
        "darkorange" if (highlight and str(row[y_col]) == highlight) else color
        for _, row in df.iterrows()
    ]
    ax.barh(df[y_col].astype(str), df[x_col], color=colors)
    if vline is not None:
        ax.axvline(vline, color="red", linestyle="--", linewidth=1, label=f"ref={vline:.2f}")
        ax.legend(fontsize=8)
    ax.set_xlabel(xlabel)
    ax.set_title(title, fontsize=11)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()
    print(f"  → {out_path.name}")


def _scatter_efficiency(df: pd.DataFrame, llm_model: str, out_path: Path):
    plt.style.use(PLT_STYLE)
    fig, ax = plt.subplots(figsize=(11, 7))

    df_c = df[df["Variante"].isin(P6_CANDIDATES)].copy()

    # Colore por equivalência ao full
    colors = [
        "#2ecc71" if s >= NOISE_FLOOR else ("#f39c12" if s >= SIGNAL_WEAK else "#e74c3c")
        for s in df_c["SoftDice_vs_full"]
    ]
    ax.scatter(df_c["TokensIn_mean"], df_c["SoftDice_vs_full"], c=colors, zorder=5, s=80)

    for _, row in df_c.iterrows():
        ax.annotate(
            row["Variante"],
            (row["TokensIn_mean"], row["SoftDice_vs_full"]),
            fontsize=7, xytext=(5, 3), textcoords="offset points",
        )

    # Linha de ruído: variantes acima dessa linha são "equivalentes ao full"
    ax.axhline(NOISE_FLOOR, color="red", linestyle="--", linewidth=1.5,
               label=f"Ruído intra-modelo ({NOISE_FLOOR:.3f}) — acima = equiv. ao full")
    ax.axhline(SIGNAL_WEAK, color="orange", linestyle=":", linewidth=1,
               label=f"Sinal fraco ({SIGNAL_WEAK:.2f})")

    ax.set_xlabel("Tokens de entrada (média por tabela, acumulado)")
    ax.set_ylabel("SoftDice semântico vs v01_full")
    ax.set_title(
        f"Fronteira de eficiência — {llm_model}\n"
        f"Verde = equivalente ao full (dentro do ruído); menor X = mais eficiente",
        fontsize=10
    )
    ax.legend(fontsize=8)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f"))
    plt.tight_layout()
    plt.savefig(out_path, dpi=180)
    plt.close()
    print(f"  → {out_path.name}")


def make_rq_plots(rq_label: str, df_summary: pd.DataFrame, llm_model: str, out_dir: Path):
    slug = rq_label.lower().replace(" ", "_")
    png = out_dir / f"{slug}_{llm_model}.png"

    is_p7 = rq_label == "P7_vs_full"
    # P7: ordenar crescente (pior primeiro); P1-P5: crescente (mais impactante primeiro)
    df_plot = df_summary.sort_values("SoftDice_mean", ascending=True).copy()

    # Colore barras por nível de significância
    def bar_color(soft):
        if is_p7:
            # P7: alto = bom
            if soft >= NOISE_FLOOR: return "#2ecc71"   # verde = equiv ao full
            elif soft >= SIGNAL_WEAK: return "#f39c12" # laranja = próximo
            else: return "#e74c3c"                      # vermelho = distante
        else:
            # P1-P5: baixo = campo importa
            if soft >= NOISE_FLOOR: return "#bdc3c7"   # cinza = dentro do ruído
            elif soft >= SIGNAL_WEAK: return "#f39c12" # laranja = sinal fraco
            elif soft >= SIGNAL_STRONG: return "#e67e22" # laranja escuro = real
            else: return "#e74c3c"                      # vermelho = forte

    colors = [bar_color(v) for v in df_plot["SoftDice_mean"]]

    plt.style.use(PLT_STYLE)
    fig, ax = plt.subplots(figsize=(11, max(4, len(df_plot) * 0.5)))
    ax.barh(df_plot["Comparacao"].astype(str), df_plot["SoftDice_mean"], color=colors)

    # Linha de ruído intra-modelo
    ax.axvline(NOISE_FLOOR, color="red", linestyle="--", linewidth=1.5,
               label=f"Ruído intra-modelo ({NOISE_FLOOR:.3f})")
    if not is_p7:
        ax.axvline(SIGNAL_WEAK, color="orange", linestyle=":", linewidth=1,
                   label=f"Limiar sinal fraco ({SIGNAL_WEAK:.2f})")
        ax.axvline(SIGNAL_STRONG, color="darkorange", linestyle=":", linewidth=1,
                   label=f"Limiar sinal forte ({SIGNAL_STRONG:.2f})")

    ax.set_xlabel("SoftDice semântico médio")
    ax.set_xlim(0, 1.05)

    if is_p7:
        title_note = "Alto = parecido com full. Verde = equivalente ao full (dentro do ruído)."
    else:
        title_note = "Baixo = campo importa. Cinza = dentro do ruído intra-modelo (irrelevante)."

    ax.set_title(f"{rq_label} — {llm_model}\n{title_note}", fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    plt.tight_layout()
    plt.savefig(png, dpi=180)
    plt.close()
    print(f"  → {png.name}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    api_key = load_env()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não encontrada no .env")

    # Descobre modelos com dados em disco
    active_models = {
        llm: path for llm, path in LLM_MODELS.items() if path.exists()
    }
    if not active_models:
        raise RuntimeError("Nenhuma pasta de input encontrada. Verifique LLM_MODELS.")
    print(f"\nModelos encontrados: {list(active_models.keys())}")

    # Carrega dados
    all_topics_per_model = {}
    all_metrics_per_model = {}
    for llm_model, input_dir in active_models.items():
        print(f"\nCarregando {llm_model}...")
        all_topics_per_model[llm_model] = load_ablation_runs(input_dir)
        all_metrics_per_model[llm_model] = load_metrics(input_dir, llm_model)

    # Gera embeddings (uma única vez para todos os modelos)
    unique_themes = collect_unique_themes(all_topics_per_model)
    emb = get_embeddings(unique_themes, api_key)
    emb_lookup = build_embedding_lookup(unique_themes, emb)

    all_raw_frames = []
    all_efficiency_frames = []

    for llm_model, input_dir in active_models.items():
        model_dir = RQ_DIR / llm_model
        model_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"  Rodando análise para: {llm_model}")
        print(f"{'='*60}")

        all_topics = all_topics_per_model[llm_model]
        metrics    = all_metrics_per_model[llm_model]

        # ── Todas as comparações dirigidas ──────────────────────────────────
        df_raw = run_research_questions(llm_model, all_topics, metrics, emb_lookup)
        df_raw["LLM_Model"] = llm_model

        df_raw.to_csv(model_dir / "all_pairwise_raw.csv", index=False)
        all_raw_frames.append(df_raw)

        # ── P1 – P5, P7: sumariza e plota ───────────────────────────────────
        for rq in ["P1_isolated_effects", "P2_numeric_stats",
                   "P3_sample_rows_vs_col_values", "P4_fk_interaction",
                   "P5_nullable_interaction", "P7_vs_full"]:
            sub = df_raw[df_raw["RQ"] == rq]
            if sub.empty:
                continue
            summary = summarize_pairs(sub)
            csv_path = model_dir / f"{rq.lower()}_{llm_model}.csv"
            summary.to_csv(csv_path, index=False)
            print(f"\n  [{rq}]")
            print(summary[["Comparacao", "SoftDice_mean", "SoftDice_std",
                            "Delta_TokensIn", "N_Tabelas"]].to_string(index=False))
            make_rq_plots(rq, summary, llm_model, model_dir)

        # ── P6 – Fronteira de eficiência ────────────────────────────────────
        eff_df = build_efficiency_df(df_raw, metrics, llm_model)
        eff_df.to_csv(model_dir / f"p6_efficiency_{llm_model}.csv", index=False)
        all_efficiency_frames.append(eff_df)
        print(f"\n  [P6_efficiency]")
        print(eff_df[["Variante", "SoftDice_vs_full",
                       "TokensIn_mean", "Tokens_per_Quality"]].to_string(index=False))
        _scatter_efficiency(eff_df, llm_model, model_dir / f"p6_efficiency_{llm_model}.png")

    # ── Consolidados multi-modelo ────────────────────────────────────────────
    if all_raw_frames:
        df_all = pd.concat(all_raw_frames, ignore_index=True)
        df_all.to_csv(OUTPUT_DIR / "all_models_pairwise_raw.csv", index=False)

        # Summary consolidado por RQ e comparação (média entre modelos)
        consolidated_summary = (
            df_all
            .groupby(["RQ", "Comparacao", "Variante_A", "Variante_B"])
            .agg(
                SoftDice_mean_all_models=("SoftDice_mean", "mean"),
                SoftDice_std_all_models=("SoftDice_mean", "std"),
                Delta_TokensIn_mean=("Delta_TokensIn", "mean"),
            )
            .reset_index()
            .sort_values(["RQ", "SoftDice_mean_all_models"], ascending=[True, False])
        )
        consolidated_summary.to_csv(
            OUTPUT_DIR / "all_models_rq_summary.csv", index=False
        )

    if all_efficiency_frames:
        pd.concat(all_efficiency_frames, ignore_index=True).to_csv(
            OUTPUT_DIR / "all_models_efficiency.csv", index=False
        )

    print(f"\n{'='*60}")
    print(f"✓ Resultados em: {RQ_DIR}")
    print(f"  Por modelo:    <RQ_DIR>/<MODELO>/")
    print(f"  Consolidado:   all_models_pairwise_raw.csv")
    print(f"                 all_models_rq_summary.csv")
    print(f"                 all_models_efficiency.csv")
    print(f"{'='*60}")

    # ── Imprime interpretação textual final ──────────────────────────────────
    if all_raw_frames:
        _print_interpretation(pd.concat(all_raw_frames, ignore_index=True))


def _signal_tag_rq(soft: float) -> str:
    """
    Classifica a diferença entre A e B (P1–P5) em relação ao ruído intra-modelo.

    Como SoftDice(A vs B) mede SOBREPOSIÇÃO entre os tópicos gerados:
      - Alto → A e B geram tópicos parecidos → o campo extra de A NÃO muda o resultado
      - Baixo → A e B geram tópicos diferentes → o campo importa

    Calibração pelo ruído empírico (menor intra = 0.861):
      ≥ NOISE_FLOOR (0.861)  → dentro do ruído → IRRELEVANTE
      SIGNAL_WEAK–NOISE_FLOOR → sinal fraco mas real → IMPACTO LEVE
      < SIGNAL_WEAK (0.800)  → claramente abaixo do ruído → IMPACTO REAL
      < SIGNAL_STRONG (0.700) → impacto forte e consistente
    """
    if soft >= NOISE_FLOOR:
        return "◦ IRRELEVANTE  (dentro do ruído intra-modelo)"
    elif soft >= SIGNAL_WEAK:
        return "▸ IMPACTO LEVE (abaixo do ruído, sinal fraco)"
    elif soft >= SIGNAL_STRONG:
        return "▶ IMPACTO REAL (sinal claro e consistente)"
    else:
        return "◆ IMPACTO FORTE (diferença muito grande)"


def _signal_tag_p7(soft: float) -> str:
    """
    Para P7 (variante vs v01_full): alto = bom = parecido com o full.
    Calibrado pelo mesmo ruído intra-modelo: se uma variante já alcança
    SoftDice ≥ NOISE_FLOOR vs o full, ela é praticamente equivalente ao full
    mesmo considerando a variabilidade natural do modelo.
    """
    if soft >= NOISE_FLOOR:
        return "✓✓ EQUIVALENTE AO FULL (dentro do ruído)"
    elif soft >= SIGNAL_WEAK:
        return "✓  PRÓXIMO DO FULL (diferença pequena)"
    elif soft >= SIGNAL_STRONG:
        return "~  DISTÂNCIA MODERADA do full"
    else:
        return "✗  DISTANTE DO FULL"


def _print_interpretation(df_all: pd.DataFrame):
    """
    Interpretação das perguntas de pesquisa calibrada pelo ruído intra-modelo.

    LÓGICA CENTRAL:
    ───────────────
    O SoftDice intra-modelo (mesma variante, mesmas entradas, runs diferentes)
    é em média ~0.90 (mínimo observado: 0.861 — Gemini/NHANES).

    Isso significa que comparar variante A vs variante B e obter SoftDice=0.87
    é INDISTINGUÍVEL do ruído natural — o campo extra de A não faz diferença
    detectável além da estocásticidade do próprio modelo.

    Limiares usados:
      NOISE_FLOOR   = 0.861  → abaixo disso, a diferença A vs B é real
      SIGNAL_WEAK   = 0.800  → sinal fraco mas fora do ruído
      SIGNAL_STRONG = 0.700  → sinal forte
    """
    print("\n" + "="*75)
    print("INTERPRETAÇÃO CALIBRADA PELO RUÍDO INTRA-MODELO")
    print(f"  Ruído intra-modelo: mínimo={NOISE_FLOOR:.3f}  |  limiares: "
          f"fraco={SIGNAL_WEAK:.3f}  forte={SIGNAL_STRONG:.3f}")
    print("="*75)

    rq_desc = {
        "P1_isolated_effects":         "P1 — Efeito isolado de cada campo sobre o baseline",
        "P2_numeric_stats":            "P2 — Numeric_stats ajuda?",
        "P3_sample_rows_vs_col_values":"P3 — Sample_rows vs valores por coluna",
        "P4_fk_interaction":           "P4 — FK acrescenta quando já há dados de valor?",
        "P5_nullable_interaction":     "P5 — Nullable acrescenta quando já há dados de valor?",
        "P7_vs_full":                  "P7 — Todas as variantes vs v01_full",
    }

    for rq, desc in rq_desc.items():
        sub = df_all[df_all["RQ"] == rq]
        if sub.empty:
            continue
        summary = (
            sub.groupby("Comparacao")["SoftDice_mean"]
            .mean()
            .sort_values(ascending=(rq != "P7_vs_full"))
            .reset_index()
        )
        print(f"\n{'─'*75}")
        print(f"  {desc}")
        if rq != "P7_vs_full":
            print(f"  [SoftDice BAIXO = diferença REAL entre A e B = campo IMPORTA]")
        else:
            print(f"  [SoftDice ALTO = variante parecida com full = campo desnecessário]")
        print(f"{'─'*75}")
        for _, row in summary.iterrows():
            soft = row["SoftDice_mean"]
            tag = _signal_tag_p7(soft) if rq == "P7_vs_full" else _signal_tag_rq(soft)
            print(f"    {row['Comparacao']:<58s}  {soft:.3f}  {tag}")

    # ── Resumo executivo ─────────────────────────────────────────────────────
    print(f"\n{'='*75}")
    print("  RESUMO EXECUTIVO (média entre todos os modelos)")
    print(f"{'='*75}")

    conclusions = []

    # P1: qual campo tem maior impacto isolado?
    p1 = df_all[df_all["RQ"] == "P1_isolated_effects"].groupby("Comparacao")["SoftDice_mean"].mean()
    if not p1.empty:
        mais_impactante = p1.idxmin()
        menos_impactante = p1.idxmax()
        conclusions.append(
            f"P1  Campo com MAIOR impacto isolado : {mais_impactante}  "
            f"(SoftDice={p1.min():.3f})"
        )
        conclusions.append(
            f"P1  Campo com MENOR impacto isolado : {menos_impactante}  "
            f"(SoftDice={p1.max():.3f}, dentro do ruído={p1.max() >= NOISE_FLOOR})"
        )

    # P2: numeric_stats é irrelevante?
    p2 = df_all[df_all["RQ"] == "P2_numeric_stats"].groupby("Comparacao")["SoftDice_mean"].mean()
    if not p2.empty:
        avg_p2 = p2.mean()
        conclusions.append(
            f"P2  Numeric_stats: SoftDice médio={avg_p2:.3f}  →  "
            f"{'IRRELEVANTE (dentro do ruído)' if avg_p2 >= NOISE_FLOOR else 'tem algum efeito'}"
        )

    # P3: rows ou col-values?
    p3 = df_all[df_all["RQ"] == "P3_sample_rows_vs_col_values"].groupby("Comparacao")["SoftDice_mean"].mean()
    if "rows vs sample_values" in p3.index and "rows vs frequent_values" in p3.index:
        rv_sv = p3["rows vs sample_values"]
        rv_fv = p3["rows vs frequent_values"]
        winner = "sample_rows" if rv_sv < rv_fv else "frequent_values"
        conclusions.append(
            f"P3  rows vs sample_values={rv_sv:.3f} | rows vs freq_values={rv_fv:.3f}  "
            f"→  {winner} é mais distinto (mais impacto)"
        )

    # P6: variante mais eficiente (maior SoftDice/token via P7)
    p7 = df_all[df_all["RQ"] == "P7_vs_full"].groupby("Variante_A").agg(
        soft=("SoftDice_mean", "mean"),
        toks=("TokensIn_A_mean", "mean"),
    )
    p7 = p7[p7["toks"].notna() & (p7["toks"] > 0)].copy()
    if not p7.empty:
        p7["efficiency"] = p7["soft"] / p7["toks"]
        best = p7["efficiency"].idxmax()
        conclusions.append(
            f"P6  Variante mais eficiente (qualidade/token): {best}  "
            f"(SoftDice={p7.loc[best,'soft']:.3f}, tokens={p7.loc[best,'toks']:.0f})"
        )

    for c in conclusions:
        print(f"  • {c}")

    print(f"\n  Referência de ruído intra-modelo (SoftDice entre execuções idênticas):")
    for model, bases in INTRA_MODEL_NOISE.items():
        vals = "  ".join(f"{b}={v:.3f}" for b, v in bases.items())
        print(f"    {model:<10s}: {vals}")
    print("="*75)


if __name__ == "__main__":
    main()