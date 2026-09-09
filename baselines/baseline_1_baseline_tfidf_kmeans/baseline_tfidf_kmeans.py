"""
Baseline: TF-IDF + K-Means sobre nomes de tabelas e colunas.

Lê o metadata.json usado no pipeline principal, escolhe automaticamente
o número de clusters usando Silhouette Score e salva:

1. JSON organizado por cluster;
2. CSV com uma linha por tabela;
3. resultados dos valores de k testados;
4. gráfico de barras com o tamanho de cada cluster (legível mesmo com k grande);
5. scatter 2D via SVD (útil para k pequeno; com k grande a legenda fica poluída).

Uso:
    python baseline_tfidf_kmeans.py <dataset>

Exemplo:
    python baseline_tfidf_kmeans.py teixeira

Também é possível informar o maior k que será testado:

    python baseline_tfidf_kmeans.py teixeira 50
"""

import csv
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score


ROOT_DIR = Path(__file__).resolve().parents[2]

DATASET = sys.argv[1] if len(sys.argv) > 1 else "nhanes"

# Agora o segundo argumento representa o maior k testado,
# e não necessariamente o k que será usado.
USER_MAX_K = int(sys.argv[2]) if len(sys.argv) > 2 else None

DATA_DIR = ROOT_DIR / "data" / DATASET
METADATA_PATH = DATA_DIR / "step2_output" / "metadata.json"

OUTPUT_DIR = DATA_DIR / "baseline_output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Rótulos de cluster que devem ser destacados (em vermelho) no gráfico
# de barras, independentemente de estarem entre os TOP_N_LABELED maiores.
# Preencha com os rótulos que você cita no texto do artigo.
HIGHLIGHT_LABELS = ["no | tb | tipo"]

# Quantos clusters (do maior para o menor) recebem rótulo de texto
# no eixo Y do gráfico de barras.
TOP_N_LABELED = 100


def load_metadata():
    with METADATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def table_to_text(table_meta: dict) -> str:
    """
    Junta o nome da tabela e os nomes das colunas em um documento.

    Não usa valores, sample_rows, estatísticas ou tipos.
    """

    table_name = table_meta.get("table_name", "")

    columns = [
        column.get("name", "")
        for column in table_meta.get("columns", [])
    ]

    text = " ".join([table_name] + columns)

    # Separa identificadores com underscore ou hífen.
    text = text.replace("_", " ").replace("-", " ")

    return text.lower()


def determine_max_k(n_tables: int) -> int:
    """
    Define automaticamente o maior número de clusters que será testado.

    Por padrão, utiliza aproximadamente 2 * sqrt(número de tabelas).
    """

    if n_tables < 3:
        raise ValueError(
            "São necessárias pelo menos três tabelas para selecionar k."
        )

    if USER_MAX_K is not None:
        max_k = USER_MAX_K
    else:
        max_k = max(10, round(2 * math.sqrt(n_tables)))

    # Silhouette precisa que k seja menor que o número de amostras.
    return min(max_k, n_tables - 1)


def select_best_k(X, max_k: int):
    """
    Testa valores de k entre 2 e max_k.

    O melhor k é aquele com maior Silhouette Score usando
    distância de cosseno.
    """

    evaluations = []

    best_model = None
    best_labels = None
    best_k = None
    best_score = float("-inf")

    print(f"Testando valores de k entre 2 e {max_k}...")

    for k in range(2, max_k + 1):
        model = KMeans(
            n_clusters=k,
            random_state=42,
            n_init=10,
        )

        labels = model.fit_predict(X)

        score = silhouette_score(
            X,
            labels,
            metric="cosine",
        )

        cluster_sizes = np.bincount(labels)

        evaluation = {
            "k": k,
            "silhouette_score": float(score),
            "inertia": float(model.inertia_),
            "smallest_cluster": int(cluster_sizes.min()),
            "largest_cluster": int(cluster_sizes.max()),
        }

        evaluations.append(evaluation)

        print(
            f"k={k:>3} | "
            f"silhouette={score:.4f} | "
            f"menor cluster={cluster_sizes.min():>3} | "
            f"maior cluster={cluster_sizes.max():>3}"
        )

        if score > best_score:
            best_score = score
            best_k = k
            best_model = model
            best_labels = labels

    return best_k, best_model, best_labels, evaluations


def get_cluster_terms(model, vectorizer, top_n=3):
    """
    Seleciona os termos de maior peso no centroide de cada cluster.
    """

    terms = vectorizer.get_feature_names_out()
    top_terms_per_cluster = {}

    number_of_terms = min(top_n, len(terms))

    for cluster_id in range(model.n_clusters):
        centroid = model.cluster_centers_[cluster_id]

        top_indices = centroid.argsort()[::-1][:number_of_terms]

        top_terms_per_cluster[cluster_id] = [
            terms[index]
            for index in top_indices
        ]

    return top_terms_per_cluster


def build_grouped_result(
    metadata,
    labels,
    top_terms_per_cluster,
    selected_k,
    evaluations,
):
    """
    Organiza o resultado principalmente por cluster.
    """

    clusters = {}

    table_to_cluster = {}

    for table_meta, label in zip(metadata, labels):
        cluster_id = int(label)

        schema = table_meta.get("schema", "")
        table_name = table_meta.get("table_name", "")
        full_name = f"{schema}.{table_name}"

        table_to_cluster[full_name] = cluster_id

        if cluster_id not in clusters:
            cluster_terms = top_terms_per_cluster[cluster_id]

            clusters[cluster_id] = {
                "cluster_id": cluster_id,
                "cluster_label": " | ".join(cluster_terms),
                "cluster_terms": cluster_terms,
                "n_tables": 0,
                "tables": [],
            }

        clusters[cluster_id]["tables"].append(full_name)
        clusters[cluster_id]["n_tables"] += 1

    # Ordena as tabelas dentro de cada cluster.
    for cluster in clusters.values():
        cluster["tables"].sort()

    # Converte o dicionário para lista e ordena pelo cluster_id.
    cluster_list = sorted(
        clusters.values(),
        key=lambda cluster: cluster["cluster_id"],
    )

    # Ranking dos valores de k, do melhor para o pior.
    ranked_evaluations = sorted(
        evaluations,
        key=lambda evaluation: evaluation["silhouette_score"],
        reverse=True,
    )

    return {
        "method": "TF-IDF + K-Means",
        "dataset": DATASET,
        "n_tables": len(metadata),
        "selected_k": selected_k,
        "selection_criterion": "highest cosine silhouette score",
        "k_evaluations": ranked_evaluations,
        "clusters": cluster_list,
        "table_to_cluster": table_to_cluster,
    }


def plot_cluster_sizes(
    grouped_result,
    output_path,
    highlight_labels=None,
    top_n_labeled=15,
):
    """
    Gráfico de barras horizontal com o tamanho de cada cluster,
    ordenado do maior para o menor.

    Mais legível que o scatter 2D quando k é grande, porque não depende
    de discriminar dezenas de cores nem de uma legenda gigante: só os
    clusters mais relevantes (os `top_n_labeled` maiores, mais qualquer
    um listado em `highlight_labels`) recebem rótulo de texto.
    """

    highlight_labels = highlight_labels or []

    clusters = sorted(
        grouped_result["clusters"],
        key=lambda cluster: cluster["n_tables"],
        reverse=True,
    )

    sizes = [cluster["n_tables"] for cluster in clusters]
    labels = [cluster["cluster_label"] for cluster in clusters]

    display_labels = []
    for index, (cluster, label) in enumerate(zip(clusters, labels)):
        if index < top_n_labeled or label in highlight_labels:
            display_labels.append(
                f"{cluster['cluster_id']}: {label} (n={cluster['n_tables']})"
            )
        else:
            display_labels.append("")

    fig_height = max(6, len(clusters) * 0.18)
    plt.figure(figsize=(10, fig_height))

    colors = [
        "#d62728" if label in highlight_labels else "#4c72b0"
        for label in labels
    ]

    y_positions = range(len(clusters))

    plt.barh(
        y_positions,
        sizes,
        color=colors,
        edgecolor="black",
        linewidth=0.3,
    )
    plt.yticks(y_positions, display_labels, fontsize=7)
    plt.gca().invert_yaxis()  # maior cluster no topo
    plt.xlabel("Número de tabelas no cluster")
    plt.title(
        f"Distribuição de tamanho dos clusters "
        f"(dataset: {grouped_result['dataset']}, k={grouped_result['selected_k']})"
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_clusters(X, labels, grouped_result, output_path):
    """
    Projeta os vetores TF-IDF em 2D (via TruncatedSVD, que funciona
    bem com matrizes esparsas) e plota os clusters com cores distintas.

    Aviso: com k grande (dezenas de clusters) a legenda fica poluída,
    pois a colormap usada só tem 20 cores distintas e passa a repetir.
    Para esses casos, prefira `plot_cluster_sizes`.
    """

    n_components = min(2, X.shape[1] - 1, X.shape[0] - 1)

    if n_components < 2:
        print("Não há dimensões suficientes para gerar o gráfico 2D.")
        return

    svd = TruncatedSVD(n_components=2, random_state=42)
    coords = svd.fit_transform(X)

    explained = svd.explained_variance_ratio_.sum() * 100

    labels = np.asarray(labels)
    unique_labels = sorted(set(labels.tolist()))

    cluster_label_by_id = {
        cluster["cluster_id"]: cluster["cluster_label"]
        for cluster in grouped_result["clusters"]
    }

    cmap = plt.get_cmap("tab20", max(len(unique_labels), 1))

    plt.figure(figsize=(11, 8))

    for i, cluster_id in enumerate(unique_labels):
        mask = labels == cluster_id
        legend_label = f"{cluster_id}: {cluster_label_by_id.get(cluster_id, '')}"

        plt.scatter(
            coords[mask, 0],
            coords[mask, 1],
            s=40,
            alpha=0.75,
            color=cmap(i),
            label=legend_label,
            edgecolors="black",
            linewidths=0.3,
        )

    plt.title(
        f"Clusters TF-IDF + K-Means (dataset: {DATASET}, k="
        f"{grouped_result['selected_k']})\n"
        f"Projeção 2D via SVD - variância explicada: {explained:.1f}%"
    )
    plt.xlabel("Componente 1")
    plt.ylabel("Componente 2")

    # Com muitos clusters a legenda completa fica ilegível; nesse caso
    # é melhor gerar a figura sem legenda e usar plot_cluster_sizes
    # para comunicar a distribuição no artigo.
    if len(unique_labels) <= 20:
        plt.legend(
            bbox_to_anchor=(1.02, 1),
            loc="upper left",
            fontsize="small",
            title="Cluster: termos principais",
        )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def save_csv(grouped_result, output_path):
    """
    Salva uma linha para cada tabela, ordenada por cluster.
    """

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            "cluster_id",
            "cluster_label",
            "n_tables_in_cluster",
            "table",
        ])

        for cluster in grouped_result["clusters"]:
            for table in cluster["tables"]:
                writer.writerow([
                    cluster["cluster_id"],
                    cluster["cluster_label"],
                    cluster["n_tables"],
                    table,
                ])


def main():
    metadata = load_metadata()

    if not metadata:
        raise ValueError("O metadata.json não contém tabelas.")

    docs = [
        table_to_text(table_meta)
        for table_meta in metadata
    ]

    vectorizer = TfidfVectorizer(
        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]+\b",
        min_df=1,
        sublinear_tf=True,
    )

    X = vectorizer.fit_transform(docs)

    max_k = determine_max_k(len(metadata))

    selected_k, model, labels, evaluations = select_best_k(
        X,
        max_k,
    )

    top_terms_per_cluster = get_cluster_terms(
        model,
        vectorizer,
        top_n=3,
    )

    grouped_result = build_grouped_result(
        metadata=metadata,
        labels=labels,
        top_terms_per_cluster=top_terms_per_cluster,
        selected_k=selected_k,
        evaluations=evaluations,
    )

    json_output_path = (
        OUTPUT_DIR
        / f"baseline_tfidf_kmeans_auto_k{selected_k}.json"
    )

    csv_output_path = (
        OUTPUT_DIR
        / f"baseline_tfidf_kmeans_auto_k{selected_k}.csv"
    )

    scatter_output_path = (
        OUTPUT_DIR
        / f"baseline_tfidf_kmeans_auto_k{selected_k}.png"
    )

    bar_output_path = (
        OUTPUT_DIR
        / f"baseline_cluster_sizes_k{selected_k}.png"
    )

    with json_output_path.open("w", encoding="utf-8") as file:
        json.dump(
            grouped_result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    save_csv(
        grouped_result,
        csv_output_path,
    )

    plot_clusters(
        X,
        labels,
        grouped_result,
        scatter_output_path,
    )

    plot_cluster_sizes(
        grouped_result,
        bar_output_path,
        highlight_labels=HIGHLIGHT_LABELS,
        top_n_labeled=TOP_N_LABELED,
    )

    best_score = max(
        evaluation["silhouette_score"]
        for evaluation in evaluations
    )

    print()
    print(f"Número de tabelas: {len(metadata)}")
    print(f"K selecionado: {selected_k}")
    print(f"Silhouette Score: {best_score:.4f}")
    print(f"JSON salvo em: {json_output_path}")
    print(f"CSV salvo em: {csv_output_path}")
    print(f"Gráfico de dispersão (scatter) salvo em: {scatter_output_path}")
    print(f"Gráfico de tamanho de clusters (barras) salvo em: {bar_output_path}")


if __name__ == "__main__":
    main()