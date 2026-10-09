"""Amostra tabelas e monta o pool de temas únicos (9 runs) por tabela.

Saídas em validação_humana_qualidade/data:
  amostra/manifesto_amostra.csv   -> uma linha por tabela amostrada (covariáveis + Dice)
  tarefas/tarefa_{item_id}.json   -> o que o avaliador vê (SEM origem dos temas)
  amostra/origens.json            -> tema -> [(sistema, run, posição)]  (restrito ao pesquisador)
  amostra/mapeamento_sistemas.json-> item -> {Sistema A/B/C: modelo}     (restrito ao pesquisador)

Uso: python 01_montar_pools.py --n 30 --piloto 4 --seed 42
Os Dice (hard/soft, intra/inter) vêm de data/{base}/step4_output/semantic_pair_audit.json; nada é recalculado.
A estratificação usa o Soft Dice inter.
"""
import argparse
import json
import random
import re

import numpy as np
import pandas as pd

from common import (BASES, MODELOS, RUNS, VAL, contexto_compacto, find_meta, load_dice,
                    load_metadata, load_topics, n_cols, n_fks, norm)

# Faixas de nº de colunas e fração da amostra em cada uma. Um sorteio proporcional quase não pega tabelas
# largas (no E-SUS, 75% têm <10 colunas e só 2% têm ≥50), então a amostra é estratificada por tamanho.
BINS = [10, 30, 50]
ROTULOS = ["<10", "10-29", "30-49", ">=50"]
FRACOES = np.array([0.25, 0.30, 0.20, 0.25])
EXCLUIR_GRUPOS = {"nhanes_admin"}   # tabelas que não são dados clínicos; esvazie o conjunto para incluí-las


def grupo_de(base, k):
    """NHANES: componente (schema). Magento/E-SUS: prefixo do nome da tabela."""
    esquema, _, tab = k.partition(".")
    return esquema if esquema not in (base, "public") else tab.split("_")[0].lower()


ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=30)
ap.add_argument("--piloto", type=int, default=4)
ap.add_argument("--seed", type=int, default=42)
args = ap.parse_args()

for d in ("amostra", "tarefas", "avaliacoes", "consolidado"):
    (VAL / d).mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(args.seed)
rows, origens, mapa = [], {}, {}
for base in BASES:
    topics, meta = load_topics(base), load_metadata(base)
    if not topics:
        raise SystemExit(f"{base}: nenhum table_topics_*.json em data\\{base}\\step3_output")
    if len(topics) < 9:
        print(f"[aviso] {base}: só {len(topics)}/9 arquivos de step3_output encontrados")
    chaves = set.intersection(*[set(v) for v in topics.values()]) & set(
        k for k in topics[next(iter(topics))] if find_meta(meta, k) is not None)
    chaves = sorted(chaves)
    print(f"{base}: universo = {len(chaves)} tabelas (metadata ∩ 9 runs)")

    df = pd.DataFrame({"base": base, "table_key": chaves})
    df["n_cols"] = [n_cols(find_meta(meta, k)) for k in chaves]
    df["n_fks"] = [n_fks(find_meta(meta, k)) for k in chaves]
    df["_k"] = df.table_key.str.lower()
    df = df.merge(pd.DataFrame(load_dice(base)), on="_k", how="left").drop(columns="_k")   # Dice já calculados (step4_output)
    faltam = int(df.dice_soft_inter.isna().sum())
    if faltam:
        print(f"  [aviso] {faltam} tabelas sem Dice no audit; usarão a mediana só para o sorteio")
    df["grupo"] = [grupo_de(base, k) for k in chaves]
    df = df[~df.grupo.isin(EXCLUIR_GRUPOS)].reset_index(drop=True)
    col_dice = "dice_soft_inter"
    df["_dice_estrat"] = df[col_dice].fillna(df[col_dice].median())
    print(f"  estratificação por {col_dice}; grupos: {df.grupo.value_counts().to_dict()}")

    def tercil(x):  # desempate aleatório (evita que empates em 0 sigam a ordem alfabética)
        return pd.qcut((x + rng.random(len(x)) * 1e-9).rank(method="first"), 3, labels=[0, 1, 2]).astype(int)

    df["tercil_dice"] = tercil(df["_dice_estrat"])

    # ---- faixas de colunas ----
    ne = len(BINS) + 1
    df["estrato_cols"] = np.digitize(df.n_cols, BINS)
    df["faixa_cols"] = df.estrato_cols.map(dict(enumerate(ROTULOS)))
    print("  tabelas por faixa de colunas:", df.faixa_cols.value_counts().reindex(ROTULOS, fill_value=0).to_dict())

    # ---- piloto: 1 tabela por faixa (uniforme dentro da faixa), fora da amostra principal ----
    pil = []
    for e in range(ne):
        ix = df.index[df.estrato_cols == e]
        if len(ix) > 1 and len(pil) < args.piloto:
            pil.append(rng.choice(ix))
    while len(pil) < min(args.piloto, len(df) - 1):
        c = rng.choice(df.index)
        if c not in pil:
            pil.append(c)
    resto = df.drop(pil)

    # ---- cotas por faixa (limitadas pelo nº de tabelas existentes; sobra vai para a faixa com maior fração) ----
    cap = resto.estrato_cols.value_counts().reindex(range(ne), fill_value=0).values
    q = np.floor(args.n * FRACOES).astype(int)
    for i in np.argsort(-(args.n * FRACOES - q))[: args.n - q.sum()]:
        q[i] += 1
    q = np.minimum(q, cap)
    while q.sum() < min(args.n, cap.sum()):
        livre = np.where(q < cap)[0]
        q[livre[np.argmax(FRACOES[livre])]] += 1

    # ---- dentro da faixa: sobre-amostra Dice baixo; 1/sqrt(tamanho do grupo) evita que um grupo domine ----
    tam = resto.groupby("grupo").grupo.transform("size")
    w = (1 + (resto.tercil_dice == 0)) / np.sqrt(tam)
    fixos = []
    if resto.grupo.nunique() <= args.n // 3:      # poucos grupos (ex.: componentes do NHANES): 1 por grupo
        for g in resto.grupo.unique():
            ix = resto.index[resto.grupo == g]
            fixos.append(rng.choice(ix, p=(w[ix] / w[ix].sum()).values))
    escolhidos = list(fixos)
    for e in range(ne):
        falta = max(q[e] - sum(resto.estrato_cols[f] == e for f in fixos), 0)
        ix = [i for i in resto.index[resto.estrato_cols == e] if i not in fixos]
        falta = min(falta, len(ix))
        if falta:
            escolhidos += list(rng.choice(ix, size=falta, replace=False, p=(w[ix] / w[ix].sum()).values))
    main = resto.loc[escolhidos].assign(piloto=False)
    n_s = main.estrato_cols.value_counts()
    main["peso_amostral"] = main.estrato_cols.map(lambda e: cap[e] / n_s[e])   # N_faixa / n_faixa (aprox.: 'fixos' não são aleatórios)
    amostra = pd.concat([df.loc[pil].assign(piloto=True, peso_amostral=np.nan), main])
    print("  amostra principal por faixa:", main.faixa_cols.value_counts().reindex(ROTULOS, fill_value=0).to_dict())

    for _, r in amostra.iterrows():
        k = r.table_key
        item_id = f"{base}__{re.sub(r'[^A-Za-z0-9_.-]', '_', k.split('.')[-1])}"
        prng = random.Random(f"{args.seed}-{item_id}")
        modelos = MODELOS[:]
        prng.shuffle(modelos)
        sis = {f"Sistema {c}": m for c, m in zip("ABC", modelos)}
        inv = {m: s for s, m in sis.items()}

        pool, listas = {}, {s: {} for s in sis}
        for (m, run), tab in topics.items():
            for pos, tema in enumerate(tab[k], 1):
                nt = norm(tema)
                pool.setdefault(nt, {"texto": tema, "origens": []})["origens"].append(
                    {"sistema": inv[m], "modelo": m, "run": run, "pos": pos})
            listas[inv[m]][str(run)] = list(tab[k])

        ids = list(pool)
        prng.shuffle(ids)                                   # ordem base; a interface re-embaralha por avaliador
        tarefa = {"item_id": item_id, "table_key": k, "base": base, "piloto": bool(r.piloto),
                  "contexto": contexto_compacto(find_meta(meta, k)),
                  "pool": [{"tema_id": f"t{i}", "texto": pool[t]["texto"]} for i, t in enumerate(ids)],
                  "listas": listas}
        (VAL / "tarefas" / f"tarefa_{item_id}.json").write_text(
            json.dumps(tarefa, ensure_ascii=False, indent=1), encoding="utf-8")
        origens[item_id] = {f"t{i}": {"texto": pool[t]["texto"], "origens": pool[t]["origens"]}
                            for i, t in enumerate(ids)}
        mapa[item_id] = sis
        rows.append({**r.drop(["tercil_dice", "_dice_estrat"]).to_dict(), "item_id": item_id,
                     "n_pool": len(ids), "seed": args.seed})

man = pd.DataFrame(rows)
man.to_csv(VAL / "amostra" / "manifesto_amostra.csv", index=False, encoding="utf-8-sig")
(VAL / "amostra" / "origens.json").write_text(json.dumps(origens, ensure_ascii=False, indent=1), encoding="utf-8")
(VAL / "amostra" / "mapeamento_sistemas.json").write_text(json.dumps(mapa, indent=1), encoding="utf-8")
print(man.groupby(["base", "piloto"]).size())
print("pool médio por tabela:", man.n_pool.mean().round(1))