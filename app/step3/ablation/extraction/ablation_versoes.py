import json
from typing import Dict, Any, Optional, Iterable
from step3.mistral import summarize_table


# =============================================================================
# INFRAESTRUTURA (sem alterações)
# =============================================================================

def _filter_stats(
    stats: Dict[str, Any],
    include_stats: bool = True,
    stats_fields: Optional[Iterable[str]] = None
) -> Dict[str, Any]:
    if not include_stats:
        return {}
    stats = stats or {}
    if stats_fields is None:
        return stats
    return {k: stats.get(k) for k in stats_fields if k in stats}


def _full_summary_dict(
    table_meta: Dict[str, Any],
    include_primary_key: bool = True,
    include_foreign_keys: bool = True,
    include_sample_rows: bool = True,
    sample_rows_limit: int = 3,
    include_nullable: bool = True,
    include_stats: bool = True,
    stats_fields: Optional[Iterable[str]] = None,
) -> dict:
    cols = table_meta.get("columns", [])
    col_samples = []
    for c in cols:
        col_dict = {"name": c.get("name"), "type": c.get("type")}
        if include_nullable:
            col_dict["nullable"] = c.get("nullable")
        if include_stats:
            col_dict["stats"] = _filter_stats(
                c.get("stats", {}), include_stats=include_stats, stats_fields=stats_fields
            )
        col_samples.append(col_dict)

    fk_info = []
    if include_foreign_keys:
        for fk in table_meta.get("foreign_keys", []):
            fk_info.append({
                "constrained_columns": fk.get("constrained_columns"),
                "referred_table": f"{fk.get('referred_schema')}.{fk.get('referred_table')}",
                "referred_columns": fk.get("referred_columns"),
            })

    summary = {
        "schema": table_meta.get("schema"),
        "table_name": table_meta.get("table_name"),
        "row_count": table_meta.get("row_count"),
        "columns": col_samples,
    }
    if include_primary_key:
        summary["primary_key"] = table_meta.get("primary_key")
    if include_foreign_keys:
        summary["foreign_keys"] = fk_info
    if include_sample_rows:
        summary["sample_rows"] = table_meta.get("sample_rows", [])[:sample_rows_limit]
    return summary


def _to_json(summary: dict) -> str:
    return json.dumps(summary, ensure_ascii=False)


def _build_summary(
    table_meta: Dict[str, Any],
    include_primary_key: bool = False,
    include_foreign_keys: bool = False,
    include_sample_rows: bool = False,
    sample_rows_limit: int = 3,
    include_nullable: bool = False,
    include_stats: bool = False,
    stats_fields: Optional[Iterable[str]] = None,
) -> str:
    full = _full_summary_dict(
        table_meta=table_meta,
        include_primary_key=include_primary_key,
        include_foreign_keys=include_foreign_keys,
        include_sample_rows=include_sample_rows,
        sample_rows_limit=sample_rows_limit,
        include_nullable=include_nullable,
        include_stats=include_stats,
        stats_fields=stats_fields,
    )
    summary = {
        "schema": full["schema"],
        "table_name": full["table_name"],
        "row_count": full["row_count"],
    }
    if include_primary_key:
        summary["primary_key"] = full.get("primary_key")
    if include_foreign_keys:
        summary["foreign_keys"] = full.get("foreign_keys", [])

    columns = []
    for c in full["columns"]:
        col = {"name": c["name"], "type": c["type"]}
        if include_nullable:
            col["nullable"] = c["nullable"]
        if include_stats:
            col["stats"] = c.get("stats", {})
        columns.append(col)
    summary["columns"] = columns

    if include_sample_rows:
        summary["sample_rows"] = full.get("sample_rows", [])

    return _to_json(summary)


# =============================================================================
# VARIANTES
#
# BASELINE FIXO em todas: schema + table_name + row_count + col.name + col.type
#
# DIMENSÕES TESTADAS (cada uma é um eixo independente):
#   A — FK / primary key
#   B — nullable
#   C — numeric_stats  (avg, min, max, stddev)
#   D — sample_values  (valores de exemplo por coluna)
#   E — frequent_values (top-N valores mais frequentes por coluna)
#   F — sample_rows  (linhas reais da tabela)
#
# ESTRUTURA DO ESTUDO:
#   Grupo 0  — baseline mínimo e referências
#   Grupo 1  — efeito isolado de cada dimensão  (+1 dimensão por vez)
#   Grupo 2  — efeito de FK combinado com cada tipo de dado de valor
#   Grupo 3  — efeito de nullable combinado com cada tipo de dado de valor
#   Grupo 4  — comparação sample_rows vs valores por coluna
#   Grupo 5  — combinações ricas (FK + nullable + dados de valor)
#   Grupo 6  — full sem stats numérico vs full completo (v7)
# =============================================================================

# ---------------------------------------------------------------------------
# GRUPO 0 — Baseline mínimo e referências
# ---------------------------------------------------------------------------

def v00_baseline(table_meta: Dict[str, Any]) -> str:
    """Baseline mínimo: só schema + table_name + row_count + col.name + col.type."""
    return _build_summary(table_meta)


def v01_full(table_meta: Dict[str, Any]) -> str:
    """Referência superior: tudo (chama mistral.summarize_table diretamente)."""
    return summarize_table(table_meta)


# ---------------------------------------------------------------------------
# GRUPO 1 — Efeito isolado de cada dimensão (+1 campo sobre o baseline)
# Pergunta: "esse campo sozinho já faz diferença?"
# ---------------------------------------------------------------------------

def v02_plus_fk(table_meta: Dict[str, Any]) -> str:
    """Baseline + FK e primary key."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
    )


def v03_plus_nullable(table_meta: Dict[str, Any]) -> str:
    """Baseline + nullable."""
    return _build_summary(
        table_meta,
        include_nullable=True,
    )


def v04_plus_numeric_stats(table_meta: Dict[str, Any]) -> str:
    """Baseline + numeric_stats (avg, min, max, stddev). Testa se estatísticas numéricas ajudam."""
    return _build_summary(
        table_meta,
        include_stats=True,
        stats_fields=["numeric_stats"],
    )


def v05_plus_sample_values(table_meta: Dict[str, Any]) -> str:
    """Baseline + sample_values por coluna. Testa se exemplos de valores ajudam."""
    return _build_summary(
        table_meta,
        include_stats=True,
        stats_fields=["sample_values"],
    )


def v06_plus_frequent_values(table_meta: Dict[str, Any]) -> str:
    """Baseline + frequent_values por coluna. Testa se valores frequentes ajudam."""
    return _build_summary(
        table_meta,
        include_stats=True,
        stats_fields=["frequent_values"],
    )


def v07_plus_sample_rows(table_meta: Dict[str, Any]) -> str:
    """Baseline + sample_rows (linhas reais da tabela). Testa se exemplos de linhas ajudam."""
    return _build_summary(
        table_meta,
        include_sample_rows=True,
    )


# ---------------------------------------------------------------------------
# GRUPO 2 — FK combinado com cada tipo de dado de valor
# Pergunta: "FK melhora quando tem dados de valor junto?"
# ---------------------------------------------------------------------------

def v08_fk_plus_sample_values(table_meta: Dict[str, Any]) -> str:
    """FK + sample_values. Compara com v10 e v13 para isolar interação FK×sample_values."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
        include_stats=True,
        stats_fields=["sample_values"],
    )


def v09_fk_plus_frequent_values(table_meta: Dict[str, Any]) -> str:
    """FK + frequent_values. Compara com v10 e v14 para isolar interação FK×frequent_values."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
        include_stats=True,
        stats_fields=["frequent_values"],
    )


def v10_fk_plus_sample_and_frequent(table_meta: Dict[str, Any]) -> str:
    """FK + sample_values + frequent_values. Testa se ambos os tipos de valor somam."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
        include_stats=True,
        stats_fields=["sample_values", "frequent_values"],
    )


def v11_fk_plus_sample_rows(table_meta: Dict[str, Any]) -> str:
    """FK + sample_rows. Compara com v10 e v15 para isolar interação FK×sample_rows."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
        include_sample_rows=True,
    )


# ---------------------------------------------------------------------------
# GRUPO 3 — Nullable combinado com cada tipo de dado de valor
# Pergunta: "nullable melhora quando tem dados de valor junto?"
# ---------------------------------------------------------------------------

def v12_nullable_plus_sample_values(table_meta: Dict[str, Any]) -> str:
    """Nullable + sample_values. Compara com v11 e v13."""
    return _build_summary(
        table_meta,
        include_nullable=True,
        include_stats=True,
        stats_fields=["sample_values"],
    )


def v13_nullable_plus_frequent_values(table_meta: Dict[str, Any]) -> str:
    """Nullable + frequent_values. Compara com v11 e v14."""
    return _build_summary(
        table_meta,
        include_nullable=True,
        include_stats=True,
        stats_fields=["frequent_values"],
    )


def v14_nullable_plus_numeric_stats(table_meta: Dict[str, Any]) -> str:
    """Nullable + numeric_stats. Compara com v11 e v12."""
    return _build_summary(
        table_meta,
        include_nullable=True,
        include_stats=True,
        stats_fields=["numeric_stats"],
    )


# ---------------------------------------------------------------------------
# GRUPO 4 — sample_rows vs valores por coluna
# Pergunta: "é melhor mandar linhas completas ou valores por coluna?"
# ---------------------------------------------------------------------------

def v15_sample_rows_vs_sample_values(table_meta: Dict[str, Any]) -> str:
    """sample_rows + sample_values juntos. Par com v15 e v13 para comparação direta."""
    return _build_summary(
        table_meta,
        include_sample_rows=True,
        include_stats=True,
        stats_fields=["sample_values"],
    )


def v16_sample_rows_vs_frequent_values(table_meta: Dict[str, Any]) -> str:
    """sample_rows + frequent_values juntos. Par com v15 e v14."""
    return _build_summary(
        table_meta,
        include_sample_rows=True,
        include_stats=True,
        stats_fields=["frequent_values"],
    )


def v17_sample_rows_plus_both_values(table_meta: Dict[str, Any]) -> str:
    """sample_rows + sample_values + frequent_values. Testa saturação de exemplos de dados."""
    return _build_summary(
        table_meta,
        include_sample_rows=True,
        include_stats=True,
        stats_fields=["sample_values", "frequent_values"],
    )


# ---------------------------------------------------------------------------
# GRUPO 5 — Combinações ricas (FK + nullable + dados de valor)
# Pergunta: "qual combinação intermediária chega mais perto do full com menos tokens?"
# ---------------------------------------------------------------------------

def v18_fk_nullable_sample_values(table_meta: Dict[str, Any]) -> str:
    """FK + nullable + sample_values. Combinação enxuta mas informativa."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
        include_nullable=True,
        include_stats=True,
        stats_fields=["sample_values"],
    )


def v19_fk_nullable_frequent_values(table_meta: Dict[str, Any]) -> str:
    """FK + nullable + frequent_values."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
        include_nullable=True,
        include_stats=True,
        stats_fields=["frequent_values"],
    )


def v20_fk_nullable_both_values(table_meta: Dict[str, Any]) -> str:
    """FK + nullable + sample_values + frequent_values."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
        include_nullable=True,
        include_stats=True,
        stats_fields=["sample_values", "frequent_values"],
    )


def v21_fk_nullable_sample_rows(table_meta: Dict[str, Any]) -> str:
    """FK + nullable + sample_rows. Sem nenhum stats por coluna."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
        include_nullable=True,
        include_sample_rows=True,
    )


def v22_fk_nullable_sample_rows_plus_frequent(table_meta: Dict[str, Any]) -> str:
    """FK + nullable + sample_rows + frequent_values. Combinação candidata a ótimo."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
        include_nullable=True,
        include_sample_rows=True,
        include_stats=True,
        stats_fields=["frequent_values"],
    )


def v23_fk_nullable_sample_rows_plus_sample_values(table_meta: Dict[str, Any]) -> str:
    """FK + nullable + sample_rows + sample_values. Outra candidata a ótimo."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
        include_nullable=True,
        include_sample_rows=True,
        include_stats=True,
        stats_fields=["sample_values"],
    )


# ---------------------------------------------------------------------------
# GRUPO 6 — Impacto do numeric_stats no contexto rico
# Pergunta: "numeric_stats acrescenta algo quando já tem tudo mais?"
# ---------------------------------------------------------------------------

def v24_full_no_numeric_stats(table_meta: Dict[str, Any]) -> str:
    """Tudo exceto numeric_stats. Par direto com v01_full para isolar o custo do numeric_stats."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
        include_nullable=True,
        include_sample_rows=True,
        include_stats=True,
        stats_fields=["null_count", "distinct_count", "null_percentage", "sample_values", "frequent_values"],
    )


def v25_full_no_sample_rows(table_meta: Dict[str, Any]) -> str:
    """Tudo exceto sample_rows. Isola o valor das linhas reais vs stats por coluna."""
    return _build_summary(
        table_meta,
        include_primary_key=True,
        include_foreign_keys=True,
        include_nullable=True,
        include_stats=True,
        stats_fields=["null_count", "distinct_count", "null_percentage", "numeric_stats", "sample_values", "frequent_values"],
    )


# =============================================================================
# DICIONÁRIO PRINCIPAL
# =============================================================================

ABLATION_VARIANTS = {
    # --- Grupo 0: baseline e referência superior ---
    "v00_baseline":                          v00_baseline,
    "v01_full":                              v01_full,

    # --- Grupo 1: efeito isolado de cada dimensão ---
    "v02_plus_fk":                           v02_plus_fk,
    "v03_plus_nullable":                     v03_plus_nullable,
    "v04_plus_numeric_stats":                v04_plus_numeric_stats,
    "v05_plus_sample_values":                v05_plus_sample_values,
    "v06_plus_frequent_values":              v06_plus_frequent_values,
    "v07_plus_sample_rows":                  v07_plus_sample_rows,

    # --- Grupo 2: FK + dados de valor ---
    "v08_fk_plus_sample_values":             v08_fk_plus_sample_values,
    "v09_fk_plus_frequent_values":           v09_fk_plus_frequent_values,
    "v10_fk_plus_sample_and_frequent":       v10_fk_plus_sample_and_frequent,
    "v11_fk_plus_sample_rows":               v11_fk_plus_sample_rows,

    # --- Grupo 3: nullable + dados de valor ---
    "v12_nullable_plus_sample_values":       v12_nullable_plus_sample_values,
    "v13_nullable_plus_frequent_values":     v13_nullable_plus_frequent_values,
    "v14_nullable_plus_numeric_stats":       v14_nullable_plus_numeric_stats,

    # --- Grupo 4: sample_rows vs valores por coluna ---
    "v15_sample_rows_vs_sample_values":      v15_sample_rows_vs_sample_values,
    "v16_sample_rows_vs_frequent_values":    v16_sample_rows_vs_frequent_values,
    "v17_sample_rows_plus_both_values":      v17_sample_rows_plus_both_values,

    # --- Grupo 5: combinações ricas candidatas a ótimo ---
    "v18_fk_nullable_sample_values":         v18_fk_nullable_sample_values,
    "v19_fk_nullable_frequent_values":       v19_fk_nullable_frequent_values,
    "v20_fk_nullable_both_values":           v20_fk_nullable_both_values,
    "v21_fk_nullable_sample_rows":           v21_fk_nullable_sample_rows,
    "v22_fk_nullable_sample_rows_plus_frequent":      v22_fk_nullable_sample_rows_plus_frequent,
    "v23_fk_nullable_sample_rows_plus_sample_values": v23_fk_nullable_sample_rows_plus_sample_values,

    # --- Grupo 6: impacto do numeric_stats no contexto rico ---
    "v24_full_no_numeric_stats":             v24_full_no_numeric_stats,
    "v25_full_no_sample_rows":               v25_full_no_sample_rows,
}


# =============================================================================
# VARIANT_ORDER para usar no script de análise (substitui o anterior)
# =============================================================================

VARIANT_ORDER = list(ABLATION_VARIANTS.keys())