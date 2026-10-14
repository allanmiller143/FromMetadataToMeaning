"""
Nomes e relatório para as regiões do SOM, para conferir se os grupos fazem sentido (sem LLM).

Regra do nome de cada região (combina dois critérios, usando só dados do pipeline):
  1) neurônio CENTRAL: o mais próximo (cosseno) do centroide dos protótipos dos neurônios da região;
  2) neurônio MAIOR EM TEMAS ÚNICOS: o que tem mais temas distintos, depois de colapsar variações
     do mesmo tema (plural, ordem das palavras, "de/da/do"), para repetições não inflarem o tamanho;
  3) um terceiro neurônio, pelo melhor equilíbrio entre os dois critérios.
O nome é o macrotema de cada um deles, separados por " | ".

Uso no main() do SOM.py, depois de calcular labels_h:

    from regioes_nomes import name_regions_combined, write_region_report, plot_regions_named

    names = name_regions_combined(labels_h, weights, themes, winners, macrothemes)
    write_region_report(labels_h, names, themes, winners, occurrences, macrothemes, qe_by_theme,
                        OUTPUT_DIR / "regioes_hier_relatorio.md",
                        OUTPUT_DIR / "regioes_hier_resumo.csv")
    plot_regions_named(labels_h, names, OUTPUT_DIR / "regioes_hier_nomes.png")
"""
import csv
import re
from collections import Counter, defaultdict

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import RegularPolygon, Patch
from matplotlib.collections import PatchCollection

from regioes import region_colors, text_color  # cores compartilhadas com as outras imagens

STOP = {"de", "da", "do", "das", "dos", "e", "em", "para", "por", "com", "a", "o", "as", "os",
        "no", "na", "nos", "nas", "ao", "aos", "um", "uma", "ou", "entre", "sobre", "sem"}


def _tokens(text):
    return [t for t in re.findall(r"[^\W_]+", str(text).lower()) if t not in STOP and len(t) > 2]


def _stem(tok):
    """Normalização leve de plural, só para comparar igualdade (não precisa ser linguisticamente perfeita)."""
    if tok.endswith("oes") and len(tok) > 5:
        return tok[:-3] + "ao"
    if tok.endswith("ais") and len(tok) > 5:
        return tok[:-3] + "al"
    if tok.endswith("ns") and len(tok) > 4:
        return tok[:-2] + "m"
    if tok.endswith("s") and len(tok) > 4:
        return tok[:-1]
    return tok


def theme_key(theme):
    """Chave de 'mesmo tema': ignora plural, ordem das palavras e conectivos.
    'agendamentos de consultas' e 'consulta agendamento' -> mesma chave."""
    return " ".join(sorted({_stem(t) for t in _tokens(theme)})) or str(theme).lower()


def unique_themes_by_neuron(themes, winners):
    """{'x_y': nº de temas distintos no neurônio, depois de colapsar variações do mesmo tema}."""
    keys = defaultdict(set)
    for theme, (x, y) in zip(themes, winners):
        keys[f"{x}_{y}"].add(theme_key(theme))
    return {n: len(k) for n, k in keys.items()}


def name_regions_combined(labels, weights, themes, winners, macrothemes, n_names=3, min_unique=3):
    """Nome da região = macrotema do neurônio CENTRAL + macrotema do neurônio com mais TEMAS ÚNICOS
    (+ um terceiro pelo melhor equilíbrio entre os dois). Devolve {região: 'A | B | C'}."""
    weights = np.asarray(weights)
    x_dim, y_dim, _ = weights.shape
    macro = {m["neuron"]: m["macrotema"] for m in macrothemes}
    uniq = unique_themes_by_neuron(themes, winners)

    names = {}
    for r in range(int(labels.max()) + 1):
        cells = [(x, y) for x in range(x_dim) for y in range(y_dim)
                 if labels[x, y] == r and f"{x}_{y}" in macro]
        if not cells:
            names[r] = "(sem temas)"
            continue
        strong = [c for c in cells if uniq.get(f"{c[0]}_{c[1]}", 0) >= min_unique] or cells
        ids = [f"{c[0]}_{c[1]}" for c in strong]
        U = np.array([uniq[i] for i in ids], dtype=float)

        W = np.array([weights[c] for c in strong])
        centroid = (W * np.sqrt(U)[:, None]).sum(axis=0) / np.sqrt(U).sum()
        Wn = W / np.maximum(np.linalg.norm(W, axis=1, keepdims=True), 1e-9)
        cn = centroid / max(np.linalg.norm(centroid), 1e-9)
        sims = Wn @ cn

        def norm01(v):
            span = v.max() - v.min()
            return (v - v.min()) / span if span > 1e-12 else np.ones_like(v)

        central = int(np.argmax(sims))
        largest = int(np.lexsort((sims, U))[-1])          # mais temas únicos; empate -> mais central
        balance = norm01(sims) + norm01(U)

        order = [central, largest] + [int(i) for i in np.argsort(balance)[::-1]]
        picks = []
        for i in order:
            m = macro[ids[i]]
            if m not in picks:
                picks.append(m)
            if len(picks) == n_names:
                break
        names[r] = " | ".join(picks)
    return names


def write_region_report(labels, names, themes, winners, occurrences, macrothemes, qe_by_theme,
                        out_md, out_csv, qe_high=0.8, top_neurons=5, top_themes=8, worst=5):
    """Relatório em Markdown (para ler) e CSV (para comparar). Para cada região: tamanho, QE,
    neurônios principais, temas mais frequentes e os temas que menos encaixam (maior QE)."""
    macro_by_neuron = {m["neuron"]: m["macrotema"] for m in macrothemes}
    k = int(labels.max()) + 1
    by_region = defaultdict(list)
    for theme, (x, y) in zip(themes, winners):
        by_region[int(labels[x, y])].append((theme, f"{x}_{y}"))

    md, rows = ["# Regiões e seus temas\n"], []
    for r in range(k):
        items = by_region.get(r, [])
        n_cells = int((labels == r).sum())
        if not items:
            md.append(f"## Região {r}: {names.get(r, '')}\n- sem temas ({n_cells} neurônios)\n")
            continue

        qes = np.array([qe_by_theme[t] for t, _ in items])
        pct_high = 100 * float((qes > qe_high).mean())
        first_words = Counter((_tokens(t) or [""])[0] for t, _ in items)
        head, head_n = first_words.most_common(1)[0]
        head_pct = 100 * head_n / len(items)

        neuron_count = Counter(n for _, n in items)
        neuron_uniq = defaultdict(set)
        for t, n in items:
            neuron_uniq[n].add(theme_key(t))
        n_unique_region = len(set().union(*neuron_uniq.values()))
        ranked = sorted(neuron_uniq, key=lambda n: (-len(neuron_uniq[n]), -neuron_count[n]))[:top_neurons]
        main_neurons = ", ".join(
            f"{macro_by_neuron.get(n, n)} ({len(neuron_uniq[n])} únicos de {neuron_count[n]})" for n in ranked)
        freq_sorted = sorted(items, key=lambda it: occurrences[it[0]], reverse=True)[:top_themes]
        freq_txt = "; ".join(f"{t} ({occurrences[t]})" for t, _ in freq_sorted)
        worst_sorted = sorted(items, key=lambda it: qe_by_theme[it[0]], reverse=True)[:worst]
        worst_txt = "; ".join(f"{t} ({qe_by_theme[t]:.2f})" for t, _ in worst_sorted)

        md.append(f"## Região {r}: {names.get(r, '')}")
        md.append(f"- **{len(items)} temas ({n_unique_region} únicos)** em {n_cells} neurônios | QE médio {qes.mean():.2f} | "
                  f"{pct_high:.0f}% dos temas com QE > {qe_high} | "
                  f"palavra inicial mais comum: \"{head}\" ({head_pct:.0f}% dos temas)")
        md.append(f"- Neurônios principais por temas únicos (macrotema): {main_neurons}")
        md.append(f"- Temas mais frequentes: {freq_txt}")
        md.append(f"- Temas que menos encaixam (maior QE): {worst_txt}\n")

        rows.append([r, names.get(r, ""), n_cells, len(items), n_unique_region, round(float(qes.mean()), 3),
                     round(pct_high, 1), head, round(head_pct, 1)])

    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["regiao", "nome", "neuronios", "temas", "temas_unicos", "qe_medio",
                    "pct_qe_alto", "palavra_inicial", "pct_palavra_inicial"])
        w.writerows(rows)
    print(f"Relatório salvo em: {out_md}\nResumo salvo em: {out_csv}")


def plot_regions_named(labels, names, out_png):
    """Colmeia com o número de cada região e uma legenda com os nomes.
    Usa as mesmas cores de plot_regions e plot_comparison."""
    x_dim, y_dim = labels.shape
    k = int(labels.max()) + 1
    cols = region_colors(labels)
    w, h = 1.0, np.sqrt(3) / 2

    fig, ax = plt.subplots(figsize=(17, 10))
    patches, colors = [], []
    for x in range(x_dim):
        for y in range(y_dim):
            xp = x * w + (-0.5 * w if y % 2 == 1 else 0.0)
            patches.append(RegularPolygon((xp, y * h), numVertices=6, radius=w / np.sqrt(3), orientation=0))
            colors.append(cols[int(labels[x, y])])
    ax.add_collection(PatchCollection(patches, facecolor=colors, edgecolor="white", linewidth=0.6))

    for r in range(k):
        xs, ys = np.where(labels == r)
        cx = np.mean([x + (-0.5 if y % 2 else 0) for x, y in zip(xs, ys)])
        cy = np.mean([y * h for y in ys])
        ax.text(cx, cy, str(r), ha="center", va="center", fontsize=11, fontweight="bold", color=text_color(cols[r]))

    def short(s, n=70):
        return s if len(s) <= n else s[: n - 1] + "…"

    handles = [Patch(facecolor=cols[r], label=f"{r}: {short(names.get(r, ''))}") for r in range(k)]
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False)
    ax.set_aspect("equal"); ax.autoscale_view(); ax.axis("off")
    ax.set_title(f"Regiões (K={k})")
    plt.tight_layout(); plt.savefig(out_png, dpi=150, bbox_inches="tight"); plt.close(fig)
    print(f"Mapa com nomes salvo em: {out_png}")