"""Utilitários comuns. Lê os dados reais do pipeline em data/{base}/... (somente leitura)."""
import json
import re
import unicodedata
from itertools import combinations, product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]                   
PIPE = ROOT / "data"                                          
VAL = ROOT / "validação_humana_qualidade" / "data"
BASES = ["magento2", "nhanes", "teixeira"]
MODELOS = ["openai", "deepseek", "mistral"]
RUNS = [1, 2, 3]
# Chaves iguais às de ESCALA em 02_interface_avaliacao.py (fonte da verdade) —
# perfeito=3 (núcleo/central), adequado=2 (correto mas impreciso), impreciso=1 (genérico/tangencial), errado=0 (incorreto).
NOTAS = {"perfeito": 3, "adequado": 2, "impreciso": 1, "errado": 0}


def norm(t: str) -> str:
    """Mesma normalização do artigo: NFD sem diacríticos, minúsculas, espaços únicos."""
    t = unicodedata.normalize("NFD", str(t))
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t.lower()).strip()


def load_topics(base):
    """{(modelo, run): {table_key: [temas]}} a partir de step3_output/table_topics_{MODELO}_{VERSAO}.json"""
    out = {}
    for m, r in product(MODELOS, RUNS):
        p = PIPE / base / "step3_output" / f"table_topics_{m}_{r}.json"
        if p.exists():
            out[(m, r)] = json.loads(p.read_text(encoding="utf-8"))
    return out


def _cols(t):
    for k in ("columns", "colunas", "cols"):
        if isinstance(t, dict) and k in t:
            return t[k]
    return []


def load_metadata(base):
    """{table_key: dict}. Aceita metadata em dict {chave: tabela} ou lista de tabelas."""
    raw = json.loads((PIPE / base / "step2_output" / "metadata.json").read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "tables" in raw:
        raw = raw["tables"]
    if isinstance(raw, dict):
        return raw
    out = {}
    for t in raw:
        nome = t.get("table_name") or t.get("table") or t.get("name")
        out[f"{base}.{nome}"] = t
    return out


def find_meta(meta, key):
    if key in meta:
        return meta[key]
    low = {k.lower(): v for k, v in meta.items()}
    if key.lower() in low:
        return low[key.lower()]
    suf = key.split(".")[-1].lower()
    for k, v in meta.items():
        if k.split(".")[-1].lower() == suf:
            return v
    return None


def n_cols(t):
    return len(_cols(t))


def n_fks(t):
    for k in ("foreign_keys", "fks", "foreign_key"):
        if isinstance(t, dict) and t.get(k):
            return len(t[k])
    return 0


def _audit_path(base):
    for p in (PIPE / base / "step4_output" / "semantic_pair_audit.json",
              PIPE / "step4_output" / base / "semantic_pair_audit.json",
              PIPE / "step4_output" / f"semantic_pair_audit_{base}.json"):
        if p.exists():
            return p
    achados = list((PIPE / base).rglob("semantic_pair_audit.json"))
    if achados:
        return achados[0]
    raise FileNotFoundError(f"semantic_pair_audit.json não encontrado para {base} (esperado em data\\{base}\\step4_output)")


def load_audit(base):
    """Dice já calculados no artigo. {'intra': {chave_minúscula: [comparações]}, 'inter': {...}}.
    Cada comparação: model(_a/_b), run_a, run_b, hard_dice, soft_dice, pairs."""
    raw = json.loads(_audit_path(base).read_text(encoding="utf-8"))
    return {k: {t.lower(): v for t, v in raw[k].items()} for k in ("intra", "inter")}


def _media(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else float("nan")


def load_dice(base):
    """Uma linha por tabela (chave em '_k', minúscula) com Dice hard/soft intra e inter, lidos do audit."""
    a = load_audit(base)
    linhas = []
    for k, intra in a["intra"].items():
        inter = a["inter"].get(k, [])
        r = {"_k": k,
             "dice_hard_intra": _media(x["hard_dice"] for x in intra), "dice_soft_intra": _media(x["soft_dice"] for x in intra),
             "dice_hard_inter": _media(x["hard_dice"] for x in inter), "dice_soft_inter": _media(x["soft_dice"] for x in inter)}
        for m in MODELOS:
            r[f"dice_soft_intra_{m}"] = _media(x["soft_dice"] for x in intra if x["model"].lower() == m)
        for m1, m2 in combinations(MODELOS, 2):
            r[f"dice_soft_inter_{m1}_{m2}"] = _media(x["soft_dice"] for x in inter
                                                    if {x["model_a"].lower(), x["model_b"].lower()} == {m1, m2})
        linhas.append(r)
    return linhas


def contexto_compacto(t, max_amostra=5):
    """Versão legível para o avaliador: uma linha por coluna, FKs como 'col -> tabela.col', 3 linhas de amostra."""
    def g(d, k):
        return (d or {}).get(k)
    cols = []
    for c in t.get("columns", []):
        s = c.get("stats") or {}
        ns = s.get("numeric_stats") or {}
        freq = ", ".join(f"{f['value']} ({f['count']})" for f in (s.get("frequent_values") or [])[:3])
        amostra = [str(v) for v in (s.get("sample_values") or [])[:max_amostra]]
        cols.append({"coluna": c.get("name"), "tipo": c.get("type"), "aceita_nulo": c.get("nullable"),
                     "distintos": s.get("distinct_count"), "pct_nulo": s.get("null_percentage"),
                     "min": g(ns, "min"), "max": g(ns, "max"), "media": g(ns, "avg"),
                     "mais_frequentes": freq, "amostra": " | ".join(amostra)})
    fks = [f"{', '.join(f.get('constrained_columns', []))} -> {f.get('referred_table')}"
           f"({', '.join(f.get('referred_columns', []))})" for f in t.get("foreign_keys", [])]
    return {"tabela": t.get("table_name"), "linhas": t.get("row_count"), "pk": t.get("primary_key", []),
            "fks": fks, "colunas": cols, "amostra_linhas": (t.get("sample_rows") or [])[:3]}