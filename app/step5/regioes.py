"""
Regiões sobre a grade hexagonal do SOM, via watershed na U-Matrix.

Uso (no main() do SOM.py, depois de treinar o som e montar o `clusters`):

    from regioes import auto_watershed_regions, describe_regions, plot_regions

    umatrix = compute_umatrix_hexagonal(som)
    winners = [som.winner(e) for e in embeddings]          # neurônio de cada tema
    labels, k = auto_watershed_regions(umatrix, embeddings, winners, k_min=8, k_max=25)
    describe_regions(labels, clusters)
    plot_regions(labels, umatrix, "regioes.png")
    export_regions_csv(labels, themes, winners, occurrences, macrothemes, qe_by_theme,
                       "regioes_temas.csv", tables_by_theme)

Se preferir fixar o número de regiões: watershed_regions(umatrix, n_regions=14)
"""
import heapq
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon
from matplotlib.collections import PatchCollection


def hex_neighbors(x, y, x_dim, y_dim):
    """Mesma vizinhança usada em compute_umatrix_hexagonal. Convenção do MiniSom (topology="hexagonal"):
    linhas ímpares deslocadas -0,5 em x (vale para y_dim par)."""
    if y % 2 == 0:
        adj = [(-1, 0), (1, 0), (0, -1), (0, 1), (1, -1), (1, 1)]
    else:
        adj = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1)]
    for dx, dy in adj:
        nx, ny = x + dx, y + dy
        if 0 <= nx < x_dim and 0 <= ny < y_dim:
            yield nx, ny


def smooth_umatrix(u, passes=1, alpha=0.5):
    """Suaviza ondulações pequenas: mistura cada célula com a média dos vizinhos."""
    x_dim, y_dim = u.shape
    for _ in range(passes):
        new = u.copy()
        for x in range(x_dim):
            for y in range(y_dim):
                vals = [u[n] for n in hex_neighbors(x, y, x_dim, y_dim)]
                new[x, y] = (1 - alpha) * u[x, y] + alpha * np.mean(vals)
        u = new
    return u


# ----------------------------------------------------------------------
# CORES COMPARTILHADAS (todas as imagens usam estas funções)
# ----------------------------------------------------------------------
def region_colors(labels):
    """Uma cor por região, sem repetir cores e com regiões vizinhas bem diferentes.
    Depende só de `labels`: a mesma partição tem as mesmas cores em qualquer imagem."""
    from matplotlib.colors import to_rgb
    palette = [to_rgb(c) for name in ("tab20", "tab20b", "tab20c") for c in plt.get_cmap(name).colors]
    x_dim, y_dim = labels.shape
    k = int(labels.max()) + 1

    neighbors = {r: set() for r in range(k)}
    for x in range(x_dim):
        for y in range(y_dim):
            for n in hex_neighbors(x, y, x_dim, y_dim):
                a, b = int(labels[x, y]), int(labels[n])
                if a != b:
                    neighbors[a].add(b)

    sizes = {r: int((labels == r).sum()) for r in range(k)}
    assigned, used = {}, set()
    for r in sorted(range(k), key=lambda r: (-sizes[r], r)):
        near = [assigned[n] for n in neighbors[r] if n in assigned]
        best, best_score = None, -1.0
        for i, c in enumerate(palette):
            if i in used:
                continue
            score = min((np.linalg.norm(np.array(c) - np.array(palette[j])) for j in near), default=9.0)
            if score > best_score + 1e-9:
                best, best_score = i, score
        if best is None:  # mais regiões que cores: reaproveita a mais distante dos vizinhos
            best = max(range(len(palette)),
                       key=lambda i: min((np.linalg.norm(np.array(palette[i]) - np.array(palette[j])) for j in near), default=9.0))
        assigned[r] = best
        used.add(best)
    return [palette[assigned[r]] for r in range(k)]


def text_color(rgb):
    """Branco sobre cores escuras, preto sobre cores claras."""
    lum = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return "white" if lum < 0.5 else "black"


def _watershed(u):
    """Watershed por inundação: uma semente em cada mínimo local; a água sobe do mais baixo ao mais alto."""
    x_dim, y_dim = u.shape
    labels = -np.ones(u.shape, dtype=int)
    heap, n_seeds = [], 0
    for x in range(x_dim):
        for y in range(y_dim):
            if all(u[x, y] <= u[n] for n in hex_neighbors(x, y, x_dim, y_dim)):
                heapq.heappush(heap, (float(u[x, y]), x, y, n_seeds))
                n_seeds += 1
    while heap:
        _, x, y, lab = heapq.heappop(heap)
        if labels[x, y] != -1:
            continue
        labels[x, y] = lab
        for n in hex_neighbors(x, y, x_dim, y_dim):
            if labels[n] == -1:
                heapq.heappush(heap, (float(u[n]), n[0], n[1], lab))
    return labels


def _merge_history(u, labels, k_min=1):
    """Funde as regiões separadas pelo 'muro' mais baixo, uma a uma, guardando como o mapa
    ficaria em cada K. Devolve (history, barrier):
      history[K] = matriz de rótulos com K regiões
      barrier[K] = altura do muro vencido ao fundir de K para K-1 (quanto maior, mais diferentes eram)."""
    x_dim, y_dim = u.shape
    labels = labels.copy()
    mins = {int(r): float(u[labels == r].min()) for r in np.unique(labels)}

    def snapshot():
        out = np.zeros_like(labels)
        for new_id, old in enumerate(sorted(mins)):
            out[labels == old] = new_id
        return out

    history = {len(mins): snapshot()}
    barrier = {}
    while len(mins) > max(k_min, 1):
        saddle = {}
        for x in range(x_dim):
            for y in range(y_dim):
                a = int(labels[x, y])
                for n in hex_neighbors(x, y, x_dim, y_dim):
                    b = int(labels[n])
                    if a != b:
                        key = (min(a, b), max(a, b))
                        h = float(max(u[x, y], u[n]))
                        if key not in saddle or h < saddle[key]:
                            saddle[key] = h
        if not saddle:
            break
        (a, b), h = min(saddle.items(), key=lambda kv: kv[1] - max(mins[kv[0][0]], mins[kv[0][1]]))
        barrier[len(mins)] = h - max(mins[a], mins[b])
        labels[labels == b] = a
        mins[a] = min(mins[a], mins.pop(b))
        history[len(mins)] = snapshot()
    return history, barrier


def _prepare(umatrix, smooth_passes):
    u = np.asarray(umatrix, dtype=float)
    return smooth_umatrix(u, passes=smooth_passes) if smooth_passes else u


def watershed_regions(umatrix, n_regions=10, smooth_passes=1):
    """Número de regiões fixo."""
    u = _prepare(umatrix, smooth_passes)
    history, _ = _merge_history(u, _watershed(u), k_min=n_regions)
    return history[min(n_regions, max(history))]


def auto_watershed_regions(umatrix, embeddings, winners, k_min=8, k_max=25, smooth_passes=1, verbose=True):
    """Escolhe o número de regiões pelo silhouette dos embeddings dos temas (métrica cosseno),
    testando todos os K entre k_min e k_max.
    `winners`: lista com o neurônio (x, y) de cada tema, na mesma ordem de `embeddings`.
    Devolve (labels, K). Também imprime a altura do muro vencido em cada fusão como segunda opinião."""
    from sklearn.metrics import silhouette_score

    u = _prepare(umatrix, smooth_passes)
    history, barrier = _merge_history(u, _watershed(u), k_min=k_min)
    embeddings = np.asarray(embeddings)

    results = {}
    for k in sorted(history):
        if not (k_min <= k <= k_max):
            continue
        lab = history[k]
        theme_labels = np.array([lab[x, y] for x, y in winners])
        if len(set(theme_labels)) < 2:
            continue
        results[k] = float(silhouette_score(embeddings, theme_labels, metric="cosine"))

    if not results:
        raise ValueError("Nenhum K na faixa pedida; ajuste k_min/k_max (o watershed inicial tem "
                         f"{max(history)} regiões).")

    best_k = max(results, key=results.get)
    if verbose:
        print(f"\nWatershed inicial: {max(history)} regiões. Silhouette por K:")
        for k in sorted(results):
            b = barrier.get(k + 1)
            extra = f"  muro vencido ao fundir {k + 1}->{k}: {b:.4f}" if b is not None else ""
            print(f"  K={k:>3}  silhouette={results[k]:.4f}{'  <-- escolhido' if k == best_k else ''}{extra}")
    return history[best_k], best_k


def describe_regions(labels, clusters, top=3):
    """Resumo textual: nº de neurônios, nº de temas e os neurônios com mais temas de cada região.
    `clusters` é o dict {(x, y): [temas]} do SOM.py."""
    for r in range(labels.max() + 1):
        neurons = [(x, y) for x in range(labels.shape[0]) for y in range(labels.shape[1]) if labels[x, y] == r]
        n_themes = sum(len(clusters.get(n, [])) for n in neurons)
        biggest = sorted(neurons, key=lambda n: len(clusters.get(n, [])), reverse=True)[:top]
        print(f"\nRegião {r}: {len(neurons)} neurônios, {n_themes} temas")
        for n in biggest:
            ts = clusters.get(n, [])
            if ts:
                print(f"   {n}: {len(ts)} temas, ex.: {ts[0]}")


def plot_regions(labels, umatrix, out_png):
    """Região = cor (mesma paleta de todas as imagens)."""
    x_dim, y_dim = labels.shape
    cols = region_colors(labels)
    patches, colors = [], []
    w, h = 1.0, np.sqrt(3) / 2
    for x in range(x_dim):
        for y in range(y_dim):
            xp = x * w + (-0.5 * w if y % 2 == 1 else 0.0)
            patches.append(RegularPolygon((xp, y * h), numVertices=6, radius=w / np.sqrt(3), orientation=0))
            colors.append(cols[int(labels[x, y])])
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.add_collection(PatchCollection(patches, facecolor=colors, edgecolor="white", linewidth=0.6))
    for r in range(labels.max() + 1):
        xs, ys = np.where(labels == r)
        cx = np.mean([x + (-0.5 if y % 2 else 0) for x, y in zip(xs, ys)])
        cy = np.mean([y * h for y in ys])
        ax.text(cx, cy, str(r), ha="center", va="center", fontsize=14, fontweight="bold", color=text_color(cols[r]))
    ax.set_aspect("equal"); ax.autoscale_view(); ax.axis("off")
    ax.set_title(f"Regiões (K={labels.max() + 1})")
    plt.tight_layout(); plt.savefig(out_png, dpi=150); plt.close(fig)


def export_regions_csv(labels, themes, winners, occurrences, macrothemes, qe_by_theme, out_csv, tables_by_theme=None):
    """Exporta um CSV com uma linha por tema: região, neurônio, macrotema do neurônio, tema,
    frequência, nº de tabelas e erro de quantização. Ordenado por região, neurônio e frequência."""
    import csv
    macro_by_neuron = {m["neuron"]: m["macrotema"] for m in macrothemes}
    rows = []
    for theme, (x, y) in zip(themes, winners):
        neuron = f"{x}_{y}"
        n_tables = len(tables_by_theme[theme]) if tables_by_theme is not None else ""
        rows.append([int(labels[x, y]), neuron, macro_by_neuron.get(neuron, ""), theme,
                     occurrences[theme], n_tables, round(float(qe_by_theme[theme]), 4)])
    rows.sort(key=lambda r: (r[0], r[1], -r[4]))
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["regiao", "neuronio", "macrotema", "tema", "frequencia", "n_tabelas", "qe"])
        w.writerows(rows)
    print(f"Exportado: {out_csv} ({len(rows)} temas)")