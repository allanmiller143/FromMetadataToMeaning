"""Consolida avaliações, desanonimiza via origens.json e calcula as métricas.
Requer: pandas numpy scipy krippendorff   (pip install krippendorff)
        openai (opcional; só usado para o Dice semântico da avaliação cega — sem o pacote
        ou sem OPENAI_API_KEY o script roda normalmente e pula só essa parte)
Saídas em data/consolidado/: julgamentos_tema.csv, metricas_por_run.csv, metricas_por_tabela.csv,
                              pares_de_runs.csv, avaliacao_cega.csv, resumo.json

Escala de notas (etapa 1 da interface, 02_interface_avaliacao.py -> ESCALA):
    perfeito=3, adequado=2, impreciso=1, errado=0   (ver NOTAS em common.py — a interface é a
    fonte da verdade; este script só obedece o que ela grava).

Nota sobre "facetas": a v1 do protocolo pedia que o avaliador agrupasse temas equivalentes
(paráfrases entre sistemas) para um cálculo de cobertura mais generoso. Essa etapa foi removida
por custo de tempo do avaliador; "cobertura" abaixo é calculada por tema_id exato do pool (sem
fundir paráfrases entre sistemas), o que é mais conservador que a v1.
"""
import json
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr

from common import NOTAS, VAL, load_audit, norm

try:
    import krippendorff
except ImportError:
    krippendorff = None

man = pd.read_csv(VAL / "amostra" / "manifesto_amostra.csv").set_index("item_id")
origens = json.loads((VAL / "amostra" / "origens.json").read_text(encoding="utf-8"))

# ---- carregar avaliações completas (descarta piloto) ----
recs = []
for f in (VAL / "avaliacoes").glob("avaliacao_*.jsonl"):
    ult = {}
    for linha in f.read_text(encoding="utf-8").splitlines():
        r = json.loads(linha)
        ult[r["item_id"]] = r
    recs += [r for r in ult.values() if r.get("completo") and not r.get("piloto")]
if not recs:
    raise SystemExit("Nenhuma avaliação completa (fora do piloto) encontrada.")

j = pd.DataFrame([{"item_id": r["item_id"], "avaliador": r["avaliador"], "tema_id": t, "nota": NOTAS[v["nota"]]}
                  for r in recs for t, v in r["julgamento_temas"].items()])
j["base"] = j.item_id.map(man.base)
j.to_csv(VAL / "consolidado" / "julgamentos_tema.csv", index=False, encoding="utf-8-sig")
resumo = {"n_avaliadores": j.avaliador.nunique(), "n_tabelas": j.item_id.nunique(), "n_julgamentos": len(j)}


# ---- confiabilidade (alpha de Krippendorff, ordinal) ----
def alpha(d):
    m = d.pivot_table(index="avaliador", columns=["item_id", "tema_id"], values="nota")
    if krippendorff is None or m.shape[0] < 2:
        return None
    return float(krippendorff.alpha(reliability_data=m.values.astype(float), level_of_measurement="ordinal"))


resumo["alpha_notas_tema"] = {"geral": alpha(j), **{b: alpha(g) for b, g in j.groupby("base")}}
resumo["alpha_por_avaliador_removido"] = {a: alpha(j[j.avaliador != a]) for a in j.avaliador.unique()}
piv = j.pivot_table(index=["item_id", "tema_id"], columns="avaliador", values="nota")
resumo["spearman_entre_avaliadores"] = {f"{a}~{b}": float(piv[a].corr(piv[b], method="spearman"))
                                        for a, b in combinations(piv.columns, 2)}

# ---- consenso humano por tema (mediana inferior) ----
cons = j.groupby(["item_id", "tema_id"]).nota.apply(lambda s: int(np.floor(np.median(s)))).rename("nota_cons").reset_index()
nota = {(r.item_id, r.tema_id): r.nota_cons for r in cons.itertuples()}

# ---- projeção para cada (item, modelo, run) ----
runs = []
for item in j.item_id.unique():
    validos_pool = {t for t in origens[item] if nota.get((item, t), 0) >= 2}
    por_run = {}
    for tid, o in origens[item].items():
        for x in o["origens"]:
            por_run.setdefault((x["modelo"], x["run"]), []).append((x["pos"], tid))
    for (m, r), lst in por_run.items():
        lst.sort()
        ns = [nota.get((item, t), np.nan) for _, t in lst]
        runs.append({"item_id": item, "base": man.base[item], "modelo": m, "run": r, "n_temas": len(ns),
                     "precisao": np.mean([n >= 2 for n in ns]), "erro": np.mean([n == 0 for n in ns]),
                     "generico": np.mean([n == 1 for n in ns]), "acc1_central": float(ns[0] == 3),
                     "nota_pos1": ns[0], "nota_pos2": ns[1] if len(ns) > 1 else np.nan,
                     "nota_pos3": ns[2] if len(ns) > 2 else np.nan,
                     "cobertura": len({t for _, t in lst if nota.get((item, t), 0) >= 2}) / max(len(validos_pool), 1)})
runs = pd.DataFrame(runs)
runs.to_csv(VAL / "consolidado" / "metricas_por_run.csv", index=False, encoding="utf-8-sig")
resumo["por_modelo"] = runs.groupby("modelo")[["precisao", "erro", "generico", "acc1_central", "cobertura"]].mean().round(3).to_dict("index")
resumo["por_base"] = runs.groupby("base")[["precisao", "erro", "generico", "acc1_central", "cobertura"]].mean().round(3).to_dict("index")
resumo["nota_media_por_posicao"] = runs[["nota_pos1", "nota_pos2", "nota_pos3"]].mean().round(3).to_dict()  # a ordem importa?

# ---- pares de runs: discordância benigna vs. erro (Dice lido do semantic_pair_audit.json) ----
LIMIAR = 0.5
audits = {b: load_audit(b) for b in runs.base.unique()}
pares = []
for item, g in runs.groupby("item_id"):
    base, k = man.base[item], man.table_key[item].lower()
    for tipo in ("intra", "inter"):
        for x in audits[base][tipo].get(k, []):
            ma, mb = x.get("model_a", x.get("model")), x.get("model_b", x.get("model"))
            pa, pb = [g[(g.modelo == m.lower()) & (g.run == r)].precisao.iloc[0] for m, r in ((ma, x["run_a"]), (mb, x["run_b"]))]
            pares.append({"item_id": item, "base": base, "mesmo_modelo": tipo == "intra", "dice_hard": x["hard_dice"],
                          "dice_soft": x["soft_dice"], "prec_a": pa, "prec_b": pb, "ambos_validos": pa == 1 and pb == 1})
pares = pd.DataFrame(pares)
pares.to_csv(VAL / "consolidado" / "pares_de_runs.csv", index=False, encoding="utf-8-sig")
resumo["discordancia_entre_modelos"] = {}
for col in ("dice_soft", "dice_hard"):
    baixo = pares[(pares[col] < LIMIAR) & (~pares.mesmo_modelo)]
    resumo["discordancia_entre_modelos"][col] = {
        "n_pares_dice_baixo": len(baixo),
        "prop_benigna_(ambos_100%_validos)": float(baixo.ambos_validos.mean()) if len(baixo) else None}

# ---- erro de consenso: temas presentes nos 3 modelos ----
cnt = [nota.get((i, t)) for i in j.item_id.unique() for t, o in origens[i].items()
       if len({x["modelo"] for x in o["origens"]}) == 3 and (i, t) in nota]
resumo["erro_de_consenso_(temas_dos_3_modelos_julgados_impreciso_ou_errado)"] = \
    float(np.mean([n <= 1 for n in cnt])) if cnt else None

# ---- avaliação cega: tema(s) livres do avaliador, escritos ANTES de ver qualquer sugestão ----
# Funciona como um "quarto sistema" independente. Comparamos com os temas de cada (modelo, run)
# e com o pool inteiro da tabela, usando a mesma lógica de Dice do artigo principal (lexical
# sempre; semântico só se `openai` + OPENAI_API_KEY estiverem disponíveis no ambiente).
cega = pd.DataFrame([{"item_id": r["item_id"], "avaliador": r["avaliador"], "temas_cegos": r.get("resposta_cega", [])}
                     for r in recs if r.get("resposta_cega")])

textos_run = {}   # (item_id, modelo, run) -> temas na ordem de posição original
for item, dic in origens.items():
    tmp = {}
    for o in dic.values():
        for x in o["origens"]:
            tmp.setdefault((x["modelo"], x["run"]), []).append((x["pos"], o["texto"]))
    for chave, lst in tmp.items():
        textos_run[(item, *chave)] = [t for _, t in sorted(lst)]


def dice_lexical(a, b):
    """Dice lexical (eq. 1 do artigo) sobre conjuntos já normalizados por common.norm()."""
    a, b = set(a), set(b)
    d = len(a) + len(b)
    return (2 * len(a & b) / d) if d else np.nan


EMB = {}
if len(cega):
    try:
        from openai import OpenAI
        _cliente = OpenAI()
        _todos = sorted({norm(t) for ts in cega.temas_cegos for t in ts} |
                        {norm(t) for lst in textos_run.values() for t in lst})
        _resp = _cliente.embeddings.create(model="text-embedding-3-large", input=_todos)
        EMB = {t: np.array(e.embedding) for t, e in zip(_todos, _resp.data)}
    except Exception as e:
        print(f"[aviso] Dice semântico da avaliação cega não calculado (sem pacote/credenciais `openai`): {e}")


def dice_semantico(a, b, tau=0.5):
    """Dice semântico (eq. 2 do artigo): embeddings + casamento húngaro + limiar tau=0.5."""
    if not EMB or not a or not b:
        return np.nan
    A, B = np.array([EMB[t] for t in a]), np.array([EMB[t] for t in b])
    S = (A @ B.T) / (np.linalg.norm(A, axis=1)[:, None] * np.linalg.norm(B, axis=1)[None, :])
    li, co = linear_sum_assignment(-S)
    total = sum(S[i, k] for i, k in zip(li, co) if S[i, k] >= tau)
    return 2 * total / (len(a) + len(b))


linhas_cego = []
for row in cega.itertuples():
    cegos_n = [norm(t) for t in row.temas_cegos]
    pool_n = [norm(o["texto"]) for o in origens[row.item_id].values()]
    for chave, alvo in textos_run.items():
        if chave[0] != row.item_id:
            continue
        _, m, r_ = chave
        alvo_n = [norm(t) for t in alvo]
        linhas_cego.append({
            "item_id": row.item_id, "base": man.base[row.item_id], "avaliador": row.avaliador,
            "modelo": m, "run": r_,
            "dice_cego_hard": dice_lexical(cegos_n, alvo_n),
            "dice_cego_soft": dice_semantico(cegos_n, alvo_n),
            "dice_cego_pool_hard": dice_lexical(cegos_n, pool_n),
            "dice_cego_pool_soft": dice_semantico(cegos_n, pool_n),
        })
cego_df = pd.DataFrame(linhas_cego)
if len(cego_df):
    cego_df.to_csv(VAL / "consolidado" / "avaliacao_cega.csv", index=False, encoding="utf-8-sig")
    resumo["avaliacao_cega"] = {
        "n_respostas": len(cega),
        "dice_hard_por_modelo": cego_df.groupby("modelo").dice_cego_hard.mean().round(3).to_dict(),
        "dice_hard_pool_medio": round(float(cego_df.dice_cego_pool_hard.mean()), 3),
    }
    if EMB:
        resumo["avaliacao_cega"]["dice_soft_por_modelo"] = cego_df.groupby("modelo").dice_cego_soft.mean().round(3).to_dict()
        resumo["avaliacao_cega"]["dice_soft_pool_medio"] = round(float(cego_df.dice_cego_pool_soft.mean()), 3)
else:
    resumo["avaliacao_cega"] = None

# ---- por tabela: qualidade x consistência x complexidade ----
tab = runs.groupby("item_id")[["precisao", "erro", "cobertura", "acc1_central"]].mean()
hum = pd.DataFrame([{"item_id": r["item_id"], "avaliador": r["avaliador"], "coesao": r["coesao"], "inter_humano": r["inter"],
                     "intra_humano": np.mean([v["intra"] for v in r["listas"].values()])} for r in recs]) \
    .groupby("item_id")[["coesao", "inter_humano", "intra_humano"]].mean()
tab = tab.join(hum).join(man)
tab.to_csv(VAL / "consolidado" / "metricas_por_tabela.csv", encoding="utf-8-sig")


def rho(x, y):
    d = tab[[x, y]].dropna() if x in tab and y in tab else pd.DataFrame()
    if len(d) < 5:
        return None
    r, p = spearmanr(d[x], d[y])
    return {"rho": round(float(r), 3), "p": round(float(p), 4), "n": len(d)}


resumo["correlacoes_spearman"] = {
    "dice_hard_inter x precisao": rho("dice_hard_inter", "precisao"),
    "dice_soft_inter x precisao": rho("dice_soft_inter", "precisao"),
    "dice_hard_intra x precisao": rho("dice_hard_intra", "precisao"),
    "dice_soft_intra x precisao": rho("dice_soft_intra", "precisao"),
    "dice_hard_inter x cobertura": rho("dice_hard_inter", "cobertura"),
    "n_cols x dice_hard_inter": rho("n_cols", "dice_hard_inter"),
    "n_cols x precisao": rho("n_cols", "precisao"),
    "coesao x dice_hard_inter": rho("coesao", "dice_hard_inter"),
    "dice_hard_inter x inter_humano": rho("dice_hard_inter", "inter_humano"),
    "dice_soft_inter x inter_humano": rho("dice_soft_inter", "inter_humano"),
    "dice_soft_inter x cobertura": rho("dice_soft_inter", "cobertura"),
    "dice_soft_inter x erro": rho("dice_soft_inter", "erro"),
    "dice_hard_intra x intra_humano": rho("dice_hard_intra", "intra_humano"),
    "dice_soft_intra x intra_humano": rho("dice_soft_intra", "intra_humano"),
}
# quadrante Dice x qualidade (limiares = medianas)
q = tab.dropna(subset=["dice_soft_inter", "precisao"])
resumo["quadrantes_dice_x_precisao"] = pd.crosstab(q.dice_soft_inter >= q.dice_soft_inter.median(),
                                                   q.precisao >= q.precisao.median()).to_dict()

(VAL / "consolidado" / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
print(json.dumps(resumo, ensure_ascii=False, indent=1, default=str))