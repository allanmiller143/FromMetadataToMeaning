
import os
import json
import random
import unicodedata
from pathlib import Path
from collections import defaultdict, Counter
from itertools import product
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from textwrap import shorten, wrap
import plotly.graph_objects as go
from dotenv import load_dotenv
from openai import OpenAI
from minisom import MiniSom
from sklearn.metrics.pairwise import cosine_similarity
from matplotlib.patches import RegularPolygon
from matplotlib.collections import PatchCollection
from matplotlib import cm

from map import build_interactive_map_v3


# ======================================================
# GLOBAL CONFIG
# ======================================================
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data" / "magento2"
INPUT_DIR = DATA_DIR / "step3_output"
OUTPUT_DIR = DATA_DIR / "step5_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODELS = ["OPENAI", "DEEPSEEK", "MISTRAL", 'GEMINI']
EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100
EMB_CACHE = OUTPUT_DIR / "theme_embeddings.npy"
BEST_PARAMS_FILE = OUTPUT_DIR / "som_best_params.json"

# ======================================================
# UTILS
# ======================================================
def load_env_vars():
    load_dotenv(ROOT_DIR / ".env")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não encontrada no arquivo .env")
    return api_key

def normalize_theme(text):
    if text is None:
        return ""
    text = str(text)
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return text.lower().strip()

def safe_list(x):
    return x if isinstance(x, list) else []

def _short(s, width=48):
    return shorten(str(s), width=width, placeholder="…")

# ======================================================
# LOAD DATA
# ======================================================
def load_all_topics():
    themes = set()
    occurrences = Counter()
    tables_by_theme = defaultdict(set)

    for model in MODELS:
        path = INPUT_DIR / f"table_topics_{model}_1.json"
        if not path.exists():
            print(f"Aviso: Arquivo não encontrado: {path}")
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for table, topics in data.items():
            for t in safe_list(topics):
                nt = normalize_theme(t)
                if nt:
                    themes.add(nt)
                    occurrences[nt] += 1
                    tables_by_theme[nt].add(table)

    if not themes:
        raise ValueError("Nenhum tema foi carregado. Verifique os arquivos de entrada.")

    return sorted(themes), occurrences, tables_by_theme

# ======================================================
# EMBEDDINGS
# ======================================================
def get_embeddings(texts, api_key):
    if EMB_CACHE.exists():
        print(f"Carregando embeddings do cache: {EMB_CACHE}")
        return np.load(EMB_CACHE)

    print(f"Gerando embeddings para {len(texts)} temas...")
    client = OpenAI(api_key=api_key)
    embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        embeddings.extend([d.embedding for d in resp.data])

    embeddings = np.asarray(embeddings, dtype=np.float32)
    np.save(EMB_CACHE, embeddings)
    return embeddings

# ======================================================
# SOM METRICS
# ======================================================
def quantization_error(som, data):
    return som.quantization_error(data)

def topographic_error(som, data):
    return som.topographic_error(data)

# ======================================================
# GRID SEARCH
# ======================================================
def grid_search_som(data):
    print("Iniciando Grid Search para otimização do SOM...")

    grid = {
        "x": [10, 12, 15],
        "y": [10, 12, 15],
        "sigma": [3.0, 5.0, 7.5],
        "learning_rate": [0.1, 0.3, 0.5],
        "iterations": [2000, 5000, 10000]
    }

    best = None
    results = []
    total_comb = int(np.prod([len(v) for v in grid.values()]))
    curr = 0

    for values in product(*grid.values()):
        params = dict(zip(grid.keys(), values))
        curr += 1

        som = MiniSom(
            params["x"], params["y"], data.shape[1],
            sigma=params["sigma"],
            learning_rate=params["learning_rate"],
            random_seed=SEED,
            topology="hexagonal"
        )

        som.random_weights_init(data)
        som.train_batch(data, params["iterations"], verbose=False)

        qe = float(quantization_error(som, data))
        te = float(topographic_error(som, data))
        score = qe + te

        entry = {**params, "qe": qe, "te": te, "score": score}
        results.append(entry)

        if best is None or score < best["score"]:
            best = entry

        if curr % 10 == 0 or curr == total_comb:
            print(f"\rProgresso: {curr}/{total_comb} combinações testadas.", end="")

    with open(BEST_PARAMS_FILE, "w", encoding="utf-8") as f:
        json.dump(best, f, indent=2, ensure_ascii=False)

    print(f"Melhores parâmetros salvos em: {BEST_PARAMS_FILE}")
    return best

# ======================================================
# U-MATRIX (HEX)
# ======================================================
def compute_umatrix_hexagonal(som):
    """
    Calcula a U-Matrix considerando vizinhança de 6 vizinhos (grade hexagonal).
    """
    weights = som.get_weights()
    x_dim, y_dim, _ = weights.shape
    umatrix = np.zeros((x_dim, y_dim), dtype=np.float32)

    for x in range(x_dim):
        for y in range(y_dim):
            if y % 2 == 0:
                adj = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1)]
            else:
                adj = [(-1, 0), (1, 0), (0, -1), (0, 1), (1, -1), (1, 1)]

            neighbors = []
            for dx, dy in adj:
                nx, ny = x + dx, y + dy
                if 0 <= nx < x_dim and 0 <= ny < y_dim:
                    neighbors.append(weights[nx, ny])

            if neighbors:
                umatrix[x, y] = float(np.mean([np.linalg.norm(weights[x, y] - n) for n in neighbors]))

    return umatrix

def plot_umatrix_hex_static_plain(umatrix, out_png, cmap="inferno"):
    """
    Plot estático da U-Matrix em colmeia hexagonal, SEM anotações de macrotemas.
    """
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    x_dim, y_dim = umatrix.shape
    patches = []
    colors = []

    hex_width = 1.0
    hex_height = np.sqrt(3) / 2 * hex_width

    for x in range(x_dim):
        for y in range(y_dim):
            x_offset = 0.5 * hex_width if (y % 2 == 1) else 0.0
            x_plot = x * hex_width + x_offset
            y_plot = y * hex_height

            hexagon = RegularPolygon(
                (x_plot, y_plot),
                numVertices=6,
                radius=hex_width / np.sqrt(3),
                orientation=0,
                facecolor='none',
                edgecolor='white',
                linewidth=0.5
            )
            patches.append(hexagon)
            colors.append(float(umatrix[x, y]))

    fig, ax = plt.subplots(figsize=(14, 12))

    pc = PatchCollection(patches, cmap=cmap, edgecolor="white", linewidth=0.5)
    pc.set_array(np.asarray(colors, dtype=np.float32))
    ax.add_collection(pc)

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.axis("off")

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.15)
    plt.colorbar(pc, cax=cax, label="Distância média (U-Matrix)")

    ax.set_title("U-Matrix (grade hexagonal - colmeia)")

    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"U-Matrix (sem anotações) salva em: {out_png}")

def plot_umatrix_hex_static(umatrix, out_png, macrothemes=None, top_n=10, cmap="inferno"):
    """
    Plot estático com células hexagonais em formato de colmeia perfeita.
    Colorbar com altura EXATAMENTE igual à colmeia.

    Args:
        umatrix: matriz U-Matrix
        out_png: caminho para salvar a figura
        macrothemes: lista de dicionários com macrotemas (opcional)
        top_n: número de macrotemas para anotar (padrão: 10)
        cmap: colormap (padrão: "inferno")
    """
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    x_dim, y_dim = umatrix.shape
    patches = []
    colors = []

    # Espaçamento correto para colmeia hexagonal flat-top
    hex_width = 1.0
    hex_height = np.sqrt(3) / 2 * hex_width

    # Mapear posições dos hexágonos
    hex_positions = {}

    for x in range(x_dim):
        for y in range(y_dim):
            # Offset horizontal para linhas ímpares (colmeia)
            x_offset = 0.5 * hex_width if (y % 2 == 1) else 0.0

            # Posição do centro do hexágono
            x_plot = x * hex_width + x_offset
            y_plot = y * hex_height

            hex_positions[(x, y)] = (x_plot, y_plot)

            # Criar hexágono com orientação 0 (flat-top) para colmeia perfeita
            hexagon = RegularPolygon(
                (x_plot, y_plot),
                numVertices=6,
                radius=hex_width / np.sqrt(3),
                orientation=0,
                facecolor='none',
                edgecolor='white',
                linewidth=0.5
            )

            patches.append(hexagon)
            colors.append(float(umatrix[x, y]))

    fig, ax = plt.subplots(figsize=(14, 12))

    # Adicionar hexágonos com cores
    pc = PatchCollection(patches, cmap=cmap, edgecolor="white", linewidth=0.5)
    pc.set_array(np.asarray(colors, dtype=np.float32))
    ax.add_collection(pc)

    # Adicionar anotações dos top N macrotemas
    if macrothemes is not None and len(macrothemes) > 0:
        top_macros = macrothemes[:min(top_n, len(macrothemes))]

        for i, macro in enumerate(top_macros, 1):
            neuron_str = macro["neuron"]  # formato "x_y"
            x_coord, y_coord = map(int, neuron_str.split("_"))

            if (x_coord, y_coord) in hex_positions:
                x_plot, y_plot = hex_positions[(x_coord, y_coord)]

                # Texto do macrotema (encurtado)
                label = _short(macro["macrotema"], 25)

                # Adicionar número do ranking
                text = f"{i}. {label}"

                # Adicionar texto com fundo branco semi-transparente
                ax.text(
                    x_plot, y_plot, text,
                    fontsize=7,
                    ha='center', va='center',
                    weight='bold',
                    color='white',
                    bbox=dict(
                        boxstyle='round,pad=0.3',
                        facecolor='black',
                        edgecolor='white',
                        alpha=0.7,
                        linewidth=0.8
                    ),
                    zorder=10
                )

    # Configurar eixos
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.axis("off")

    # Criar colorbar com altura EXATA do gráfico usando make_axes_locatable
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.15)
    cbar = plt.colorbar(pc, cax=cax, label="Distância média (U-Matrix)")

    # Título
    title = f"U-Matrix (grade hexagonal - colmeia)"
    if macrothemes:
        title += f"\nTop {min(top_n, len(macrothemes))} macrotemas anotados"
    ax.set_title(title)

    plt.tight_layout()
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"U-Matrix salva em: {out_png}")

# ======================================================
# EXPORT HELPERS
# ======================================================
def export_macrothemes_table(macrothemes, out_csv, top_n=40, max_subthemes=10):
    rows = []
    for i, m in enumerate(macrothemes[:top_n], 1):
        subs = m["subtemas"]
        rows.append({
            "Ranking": i,
            "Macrotema": m["macrotema"],
            "Frequência Total": m["frequencia_total"],
            "Qtd Subtemas": m["num_subtemas"],
            "Exemplos Subtemas": ", ".join(subs[:max_subthemes]) + ("..." if len(subs) > max_subthemes else ""),
            "Neurônio": m["neuron"]
        })
    pd.DataFrame(rows).to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Tabela de macrotemas salva em: {out_csv}")

def export_outliers_table(outliers, theme_to_neuron, occurrences, out_csv, top_n=40):
    rows = []
    for i, o in enumerate(outliers[:top_n], 1):
        t = o["tema"]
        rows.append({
            "Ranking": i,
            "Tema": t,
            "Erro Quantização (QE)": f"{o['qe']:.4f}",
            "Frequência": occurrences[t],
            "Neurônio": theme_to_neuron.get(t, "N/A")
        })
    pd.DataFrame(rows).to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Tabela de outliers salva em: {out_csv}")

def export_cluster_theme_tables(macrothemes, tables_by_theme, occurrences, out_csv):
    """
    Exporta uma tabela detalhada contendo:
    Macrotema | Tema (Subtema) | Frequência do Tema | Tabelas de Origem
    """
    rows = []
    for m in macrothemes:
        macro_name = m["macrotema"]
        for theme in m["subtemas"]:
            tables = sorted(list(tables_by_theme.get(theme, [])))
            rows.append({
                "Macrotema": macro_name,
                "Tema": theme,
                "Frequência": occurrences[theme],
                "Tabelas de Origem": "; ".join(tables),
                "Qtd Tabelas": len(tables)
            })
    
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Tabela detalhada de clusters salva em: {out_csv}")

def export_tables_by_cluster(macrothemes, tables_by_theme, out_csv):
    """
    Exporta uma tabela resumida por Macrotema e as tabelas que o compõem.
    """
    rows = []
    for m in macrothemes:
        macro_name = m["macrotema"]
        all_tables = set()
        for theme in m["subtemas"]:
            all_tables.update(tables_by_theme.get(theme, []))
        
        rows.append({
            "Macrotema": macro_name,
            "Qtd Temas": m["num_subtemas"],
            "Frequência Total": m["frequencia_total"],
            "Qtd Tabelas Únicas": len(all_tables),
            "Tabelas": "; ".join(sorted(list(all_tables)))
        })
    
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"Resumo de tabelas por cluster salvo em: {out_csv}")

# ======================================================
# PLOTS
# ======================================================
def plot_top_macrothemes_bar(macrothemes, out_png, top_n=20):
    top = macrothemes[:top_n]
    names = [m["macrotema"] for m in top]
    freqs = [m["frequencia_total"] for m in top]

    plt.figure(figsize=(12, 8))
    bars = plt.barh(range(len(names)), freqs, color="skyblue", edgecolor="navy", alpha=0.7)
    plt.yticks(range(len(names)), names)
    plt.gca().invert_yaxis()
    plt.xlabel("Frequência Total (Soma das ocorrências dos subtemas)")
    plt.title(f"Top {top_n} Macrotemas por Frequência")
    
    for i, bar in enumerate(bars):
        plt.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, 
                 f"{freqs[i]}", va='center', fontsize=9)

    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()

def compute_hits_matrix(x, y, winners):
    hits = np.zeros((x, y))
    for w in winners:
        hits[w[0], w[1]] += 1
    return hits

def plot_hits_heatmap(hits, out_png):
    plt.figure(figsize=(10, 8))
    plt.imshow(hits.T, cmap="YlGnBu", origin="lower")
    plt.colorbar(label="Número de Temas")
    plt.title("Hits Map (Densidade de Temas por Neurônio)")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()

def plot_scatter_winners(x, y, winners, out_png):
    wx = [w[0] for w in winners]
    wy = [w[1] for w in winners]
    
    # Adicionar jitter para visualização
    wx_j = [v + random.uniform(-0.3, 0.3) for v in wx]
    wy_j = [v + random.uniform(-0.3, 0.3) for v in wy]

    plt.figure(figsize=(10, 8))
    plt.scatter(wx_j, wy_j, alpha=0.5, s=10, c="teal")
    plt.title("Distribuição de Temas no Grid SOM (com Jitter)")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()

# ======================================================
# METADATA LOADER
# ======================================================
def load_metadata_json(path):
    if not path.exists():
        print(f"Aviso: Metadata não encontrada em {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Se for uma lista, converter para dict indexado pelo nome da tabela
            if isinstance(data, list):
                return {item.get("table_name", item.get("name", "unknown")): item for item in data}
            return data
    except Exception as e:
        print(f"Erro ao carregar metadata: {e}")
        return {}

# ======================================================
# INTERACTIVE MAP (D3.js)
# ======================================================

# ======================================================
# MAIN
# ======================================================
def main():
    print("\n=== SOM PIPELINE - COLMEIA HEXAGONAL COM ANOTAÇÕES ===\n")

    api_key = load_env_vars()

    try:
        themes, occurrences, tables_by_theme = load_all_topics()
        print(f"Quantidade de temas: {len(themes)}")
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        return

    embeddings = get_embeddings(themes, api_key)

    if BEST_PARAMS_FILE.exists():
        print(f"Usando parâmetros otimizados existentes: {BEST_PARAMS_FILE}")
        with open(BEST_PARAMS_FILE, "r", encoding="utf-8") as f:
            best = json.load(f)
    else:
        best = grid_search_som(embeddings)

    print(f"Treinando modelo final com grade {best['x']}x{best['y']}...")
    som = MiniSom(
        best["x"], best["y"], embeddings.shape[1],
        sigma=best["sigma"],
        learning_rate=best["learning_rate"],
        random_seed=SEED,
        topology="hexagonal"
    )

    som.random_weights_init(embeddings)
    som.train_batch(embeddings, best["iterations"], verbose=True)

    # ASSIGNMENTS & METRICS
    clusters = defaultdict(list)
    qe_by_theme = {}
    weights = som.get_weights()

    for i, theme in enumerate(themes):
        neuron = som.winner(embeddings[i])
        clusters[neuron].append(theme)
        qe_by_theme[theme] = float(np.linalg.norm(embeddings[i] - weights[neuron[0], neuron[1]]))

    # MACROTEMAS
    theme_to_idx = {t: i for i, t in enumerate(themes)}
    macrothemes = []

    for neuron, theme_list in clusters.items():
        idxs = [theme_to_idx[t] for t in theme_list]
        cluster_embs = embeddings[idxs]
        centroid = cluster_embs.mean(axis=0, keepdims=True)
        sims = cosine_similarity(centroid, cluster_embs)[0]
        rep = theme_list[int(np.argmax(sims))]

        macrothemes.append({
            "macrotema": rep,
            "neuron": f"{neuron[0]}_{neuron[1]}",
            "subtemas": theme_list,
            "frequencia_total": int(sum(occurrences[t] for t in theme_list)),
            "num_subtemas": int(len(theme_list))
        })

    macrothemes.sort(key=lambda x: x["frequencia_total"], reverse=True)

    with open(OUTPUT_DIR / "som_macrothemes.json", "w", encoding="utf-8") as f:
        json.dump(macrothemes, f, indent=2, ensure_ascii=False)

    # OUTLIERS
    threshold = float(np.percentile(list(qe_by_theme.values()), 95))
    outliers = [{"tema": t, "qe": qe} for t, qe in qe_by_theme.items() if qe > threshold]
    outliers.sort(key=lambda x: x["qe"], reverse=True)

    with open(OUTPUT_DIR / "som_outliers.json", "w", encoding="utf-8") as f:
        json.dump(outliers, f, indent=2, ensure_ascii=False)

    # VISUALIZAÇÃO - U-MATRIX COLMEIA COM ANOTAÇÕES
    print("\n Gerando visualização em formato de colmeia com anotações...")
    umatrix = compute_umatrix_hexagonal(som)

    # 1) Figura COLMEIA para o artigo com TOP 10 macrotemas anotados
    plot_umatrix_hex_static(
        umatrix, 
        OUTPUT_DIR / "fig_umatrix_hex_colmeia.png",
        macrothemes=macrothemes,
        top_n=10
    )

    plot_umatrix_hex_static_plain(
        umatrix,
        OUTPUT_DIR / "fig_umatrix_hex_colmeia_sem_labels.png"
    )

    # RELATÓRIOS
    theme_to_neuron = {}
    winners = []

    for i, theme in enumerate(themes):
        neuron = som.winner(embeddings[i])
        winners.append(neuron)
        theme_to_neuron[theme] = f"{neuron[0]}_{neuron[1]}"

    export_macrothemes_table(macrothemes, OUTPUT_DIR / "som_macrothemes_table.csv", top_n=40, max_subthemes=10)
    export_outliers_table(outliers, theme_to_neuron, occurrences, OUTPUT_DIR / "som_outliers_table.csv", top_n=40)
    plot_top_macrothemes_bar(macrothemes, OUTPUT_DIR / "fig_top_macrothemes.png", top_n=20)

    # TABELAS DE TEMAS E TABELAS POR CLUSTER
    print("\nGerando tabelas de temas e tabelas de origem por cluster...")
    export_cluster_theme_tables(
        macrothemes, tables_by_theme, occurrences,
        OUTPUT_DIR / "som_cluster_temas_tabelas.csv"
    )
    export_tables_by_cluster(
        macrothemes, tables_by_theme,
        OUTPUT_DIR / "som_tabelas_por_cluster.csv"
    )

    hits = compute_hits_matrix(best["x"], best["y"], winners)
    plot_hits_heatmap(hits, OUTPUT_DIR / "fig_som_hits.png")
    plot_scatter_winners(best["x"], best["y"], winners, OUTPUT_DIR / "fig_som_scatter_winners.png")

    # CARREGANDO METADATA
    print("\nCarregando metadata das tabelas...")
    metadata_path = DATA_DIR / "step2_output" / "metadata.json"
    metadata_dict = load_metadata_json(metadata_path)
    print(f"Metadata carregada: {len(metadata_dict)} tabelas encontradas")

    # NOVO MAPA INTERATIVO REFINADO COM MODAL
    build_interactive_map_v3(
        som, themes, embeddings, macrothemes, occurrences, tables_by_theme,
        OUTPUT_DIR / "mapa_interativo_refinado.html",
        umatrix,
        metadata_dict=metadata_dict
    )

if __name__ == "__main__":
    main()