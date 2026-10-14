"""
Regiões sobre a grade hexagonal do SOM via clustering hierárquico com restrição de vizinhança.

Diferença para o watershed (regioes.py): em vez de olhar só a altura dos muros da U-Matrix,
usa os vetores de pesos completos de cada neurônio (linkage Ward) e só permite juntar neurônios
que são vizinhos na grade. Por construção as regiões saem contíguas.

Reaproveita funções do regioes.py (mesma pasta), então os resultados (`labels`) têm o mesmo
formato e funcionam com describe_regions, plot_regions e export_regions_csv.

Uso no main() do SOM.py (depois de treinar o som):

    from regioes import watershed_regions, auto_watershed_regions, describe_regions, plot_regions, export_regions_csv
    from regioes_hier import auto_hier_regions, compare_regions, plot_comparison

    weights = som.get_weights()
    winners = [som.winner(e) for e in embeddings]

    labels_ws, k_ws = auto_watershed_regions(umatrix, embeddings, winners, k_min=8, k_max=25)
    labels_h,  k_h  = auto_hier_regions(weights, embeddings, winners, k_min=8, k_max=25)

    compare_regions(labels_ws, labels_h, embeddings, winners, names=("watershed", "hierarquico"))
    plot_comparison(labels_ws, labels_h, "comparacao_regioes.png", ("Watershed", "Hierárquico"))
"""
from collections import Counter

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon
from matplotlib.collections import PatchCollection
from scipy.sparse import lil_matrix

from regioes import hex_neighbors, region_colors, text_color  # vizinhança e cores compartilhadas


def _grid_connectivity(x_dim, y_dim):
    """Matriz esparsa de adjacência da grade hexagonal (índice = x * y_dim + y)."""
    n = x_dim * y_dim
    conn = lil_matrix((n, n), dtype=int)
    for x in range(x_dim):
        for y in range(y_dim):
            for nx, ny in hex_neighbors(x, y, x_dim, y_dim):
                conn[x * y_dim + y, nx * y_dim + ny] = 1
    return conn.tocsr()


def _renumber(flat_labels, x_dim, y_dim):
    """Renumera 0..K-1 pela ordem de aparição varrendo a grade (resultado estável e legível)."""
    mapping, out = {}, np.zeros(len(flat_labels), dtype=int)
    for i, lab in enumerate(flat_labels):
        if lab not in mapping:
            mapping[lab] = len(mapping)
        out[i] = mapping[lab]
    return out.reshape(x_dim, y_dim)


def _fit(weights, n_clusters, linkage="ward"):
    from sklearn.cluster import AgglomerativeClustering
    x_dim, y_dim, d = weights.shape
    W = weights.reshape(-1, d)
    model = AgglomerativeClustering(n_clusters=n_clusters, linkage=linkage,
                                    connectivity=_grid_connectivity(x_dim, y_dim))
    return _renumber(model.fit_predict(W), x_dim, y_dim)


def hier_regions(weights, n_regions=12, linkage="ward"):
    """Número de regiões fixo. `weights` = som.get_weights() (x_dim, y_dim, dim)."""
    return _fit(np.asarray(weights), n_regions, linkage)


def auto_hier_regions(weights, embeddings, winners, k_min=8, k_max=50, linkage="ward", verbose=True):
    """Escolhe K pelo silhouette (cosseno) dos embeddings dos temas, como em auto_watershed_regions.
    Imprime também a distância de fusão (Ward) de K+1 -> K como segunda opinião: um salto grande
    indica que a partir dali você começa a juntar grupos realmente diferentes."""
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import silhouette_score

    weights = np.asarray(weights)
    embeddings = np.asarray(embeddings)
    x_dim, y_dim, d = weights.shape
    n = x_dim * y_dim

    tree = AgglomerativeClustering(n_clusters=None, distance_threshold=0, linkage=linkage,
                                   connectivity=_grid_connectivity(x_dim, y_dim),
                                   compute_distances=True).fit(weights.reshape(-1, d))
    dist = tree.distances_  # dist[m] = distância da (m+1)-ésima fusão; n clusters -> n-1 apos m=1

    results, labels_by_k = {}, {}
    for k in range(k_min, k_max + 1):
        lab = _fit(weights, k, linkage)
        theme_labels = np.array([lab[x, y] for x, y in winners])
        if len(set(theme_labels)) < 2:
            continue
        results[k] = float(silhouette_score(embeddings, theme_labels, metric="cosine"))
        labels_by_k[k] = lab

    if not results:
        raise ValueError("Nenhum K válido na faixa pedida.")
    best_k = max(results, key=results.get)

    if verbose:
        print("\nHierárquico (Ward com vizinhança). Silhouette por K:")
        for k in sorted(results):
            jump = dist[n - k - 1] if 0 <= n - k - 1 < len(dist) else None
            extra = f"  fusao {k + 1}->{k}: {jump:.3f}" if jump is not None else ""
            print(f"  K={k:>3}  silhouette={results[k]:.4f}{'  <-- escolhido' if k == best_k else ''}{extra}")
    return labels_by_k[best_k], best_k


# ----------------------------------------------------------------------
# COMPARAÇÃO ENTRE DUAS PARTIÇÕES (ex.: watershed x hierárquico)
# ----------------------------------------------------------------------
def is_contiguous(labels):
    """Cada região forma um único bloco conexo na grade?"""
    x_dim, y_dim = labels.shape
    for r in np.unique(labels):
        cells = {(x, y) for x in range(x_dim) for y in range(y_dim) if labels[x, y] == r}
        seen, stack = set(), [next(iter(cells))]
        while stack:
            c = stack.pop()
            if c in seen:
                continue
            seen.add(c)
            stack += [nb for nb in hex_neighbors(c[0], c[1], x_dim, y_dim) if nb in cells]
        if seen != cells:
            return False
    return True


def compare_regions(labels_a, labels_b, embeddings, winners, names=("A", "B"), top=3):
    """Imprime métricas de cada partição e como as regiões de A se redistribuem em B."""
    from sklearn.metrics import silhouette_score, adjusted_rand_score, davies_bouldin_score

    embeddings = np.asarray(embeddings)
    ta = np.array([labels_a[x, y] for x, y in winners])
    tb = np.array([labels_b[x, y] for x, y in winners])

    print("\n=== COMPARAÇÃO ===")
    for name, lab, theme_lab in ((names[0], labels_a, ta), (names[1], labels_b, tb)):
        sil = silhouette_score(embeddings, theme_lab, metric="cosine")
        db = davies_bouldin_score(embeddings, theme_lab)
        sizes = sorted(Counter(theme_lab).values(), reverse=True)
        print(f"{name:>12}: K={lab.max() + 1:>2}  silhouette={sil:.4f}  Davies-Bouldin={db:.3f}  "
              f"contíguas={is_contiguous(lab)}  maior região={sizes[0]} temas, menor={sizes[-1]}")
    print(f"Concordância entre as duas (Adjusted Rand Index, 1 = idênticas): "
          f"{adjusted_rand_score(ta, tb):.3f}")

    print(f"\nComo cada região de {names[0]} se distribui em {names[1]} (% dos temas):")
    for ra in sorted(set(ta)):
        mask = ta == ra
        dist = Counter(tb[mask])
        parts = ", ".join(f"{names[1]} {rb}: {100 * c / mask.sum():.0f}%" for rb, c in dist.most_common(top))
        print(f"  {names[0]} {ra:>2} ({mask.sum():>3} temas) -> {parts}")


def _draw(ax, labels, title):
    x_dim, y_dim = labels.shape
    cols = region_colors(labels)
    w, h = 1.0, np.sqrt(3) / 2
    patches, colors = [], []
    for x in range(x_dim):
        for y in range(y_dim):
            xp = x * w + (-0.5 * w if y % 2 == 1 else 0.0)
            patches.append(RegularPolygon((xp, y * h), numVertices=6, radius=w / np.sqrt(3), orientation=0))
            colors.append(cols[int(labels[x, y])])
    ax.add_collection(PatchCollection(patches, facecolor=colors, edgecolor="white", linewidth=0.6))
    for r in range(labels.max() + 1):
        xs, ys = np.where(labels == r)
        cx = np.mean([x + (-0.5 if y % 2 else 0) for x, y in zip(xs, ys)])
        cy = np.mean([y * h for y in ys])
        ax.text(cx, cy, str(r), ha="center", va="center", fontsize=12, fontweight="bold", color=text_color(cols[r]))
    ax.set_aspect("equal"); ax.autoscale_view(); ax.axis("off")
    ax.set_title(f"{title} (K={labels.max() + 1})")


def plot_comparison(labels_a, labels_b, out_png, titles=("A", "B")):
    """Duas colmeias lado a lado."""
    fig, axes = plt.subplots(1, 2, figsize=(22, 9))
    _draw(axes[0], labels_a, titles[0])
    _draw(axes[1], labels_b, titles[1])
    plt.tight_layout(); plt.savefig(out_png, dpi=150); plt.close(fig)
    print(f"Comparação salva em: {out_png}")