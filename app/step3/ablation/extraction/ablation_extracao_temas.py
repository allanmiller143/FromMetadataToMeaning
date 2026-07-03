import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # app/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Importa o que precisamos do script original (sem rodar o main)
from step3.mistral import (
    load_env,
    load_metadata,
    llm_suggest_topics_with_meta,
    is_token_limit_error,
    summarize_table_compact,   # fallback de token igual ao original
    ROOT_DIR,
    DATA_DIR,
    MODEL_NAME,
)
from step3.ablation.extraction.ablation_versoes import ABLATION_VARIANTS

# ---------------------------------------------------------------------------
# Configuração de saída
# ---------------------------------------------------------------------------

ABLATION_DIR = DATA_DIR / "step3_output" / "step3_ablation_mistral"
ABLATION_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Argumentos CLI
# ---------------------------------------------------------------------------

args = sys.argv[1:]
RUN = 1
requested = [a for a in args if not a.isdigit()]
variants_to_run = (
    {k: ABLATION_VARIANTS[k] for k in requested if k in ABLATION_VARIANTS}
    if requested
    else ABLATION_VARIANTS
)

if not variants_to_run:
    print(f"Nenhuma variante válida. Disponíveis: {list(ABLATION_VARIANTS.keys())}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_variant(client, metadata, variant_name: str, summarize_fn):
    out_dir = ABLATION_DIR / variant_name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path       = out_dir / f"table_topics_{MODEL_NAME}_{RUN}.json"
    metrics_path   = out_dir / f"metrics_{MODEL_NAME}_{RUN}.json"

    table_topics  = {}
    table_metrics = {}   # { full_name: {tokens_in, tokens_out, elapsed_s, fallback} }

    variant_start = time.perf_counter()

    print(f"\n{'='*60}")
    print(f"Variante: {variant_name}  |  Run: {RUN}")
    print(f"Saída:    {out_path}")
    print(f"Métricas: {metrics_path}")
    print(f"{'='*60}")

    tables = [
        'tb_medicao',
        # 'tb_tipo_glicemia', 
        # 'tb_cidadao',
        # 'tb_exame_hemoglobina_glicada',
        # 'tb_proced_exame_especifico', 
        # 'tb_antecedente', 
        # 'tb_evolucao_subjetivo',
        # 'tb_fat_atend_odonto_problemas',
        # 'tb_odontograma',
        # 'tb_evolucao_odonto',
        # "tb_lembrete_evolucao",
        # "tb_raca_cor", 
        # 'tb_problema',
        # 'tb_medicamento_uso_continuo',
        # 'tb_ciap_ms',
        # 'tb_justificativa_prontuario',
        # 'ta_tecido_mole', 
        # 'tb_fat_rel_op_risco_cardio',
        # 'ta_vacinacao', 
        # 'tb_exame_prenatal',
        # 'tb_cuidado_compartilhado_evol',
        # 'tb_historico_dados_fao',
        # 'ta_medicamento_catmat', 
        # 'tb_dim_catmat',
        # 'tb_medicamento',
    ]

    # tables = [
    #     'dsqids_j',
    #     'dsqtot_j',
    #     'ds2tot_j',
    #     'ds2ids_j',
    #     'ds1tot_j',
    #     'bmx_j',
    #     'bpx_j',
    #     'bpxo_j',
    #     'cbc_j',
    #     'fastqx_j',
    #     'ghb_j',
    #     'hepa_j',
    #     'ins_j',
    #     'phthte_j',
    #     'uio_j',
    #     'alq_j',
    #     'smqshs_j',
    #     'puqmec_j',
    #     'demo_j',
    #     'whq_j',
    #     'hsq_j',
    #     'dpq_j',
    #     'vic_j',
    #     'vid_j',
    #     'ssuvcm_j'
    # ]

    for idx, table_meta in enumerate(metadata, 1):
        if table_meta.get('table_name') not in tables:
            continue

        full_name = f"{table_meta.get('schema')}.{table_meta.get('table_name')}"
        print(f"  [{idx}/{len(metadata)}] {full_name}", end=" ", flush=True)

        fallback_used = False
        t0 = time.perf_counter()

        try:
            try:
                summary = summarize_fn(table_meta)
                print("\n--- METADATA ENVIADO ---")
                print(json.dumps(json.loads(summary), ensure_ascii=False, indent=2)[:4000])
                print("--- FIM METADATA ---\n")     


                topics, tok_in, tok_out = llm_suggest_topics_with_meta(client, summary)
            except Exception as e:
                if is_token_limit_error(e):
                    print("(fallback compact)", end=" ", flush=True)
                    fallback_used = True
                    summary = summarize_table_compact(table_meta)
                    topics, tok_in, tok_out = llm_suggest_topics_with_meta(client, summary)
                else:
                    raise e

            elapsed = round(time.perf_counter() - t0, 3)

            table_topics[full_name]  = topics
            table_metrics[full_name] = {
                "tokens_in":    tok_in,
                "tokens_out":   tok_out,
                "tokens_total": tok_in + tok_out,
                "elapsed_s":    elapsed,
                "fallback":     fallback_used,
            }

            print(f"| {tok_in}in {tok_out}out {elapsed}s → {topics}")

        except Exception as e:
            elapsed = round(time.perf_counter() - t0, 3)
            print(f"  ERRO ({elapsed}s): {e}")
            table_topics[full_name]  = []
            table_metrics[full_name] = {
                "tokens_in":    0,
                "tokens_out":   0,
                "tokens_total": 0,
                "elapsed_s":    elapsed,
                "fallback":     fallback_used,
                "error":        str(e),
            }

    # --- sumário da variante ---
    variant_elapsed = round(time.perf_counter() - variant_start, 3)
    total_in  = sum(m["tokens_in"]  for m in table_metrics.values())
    total_out = sum(m["tokens_out"] for m in table_metrics.values())

    summary_block = {
        "_summary": {
            "variant":          variant_name,
            "run":              RUN,
            "tables_processed": len(table_metrics),
            "total_tokens_in":  total_in,
            "total_tokens_out": total_out,
            "total_tokens":     total_in + total_out,
            "total_elapsed_s":  variant_elapsed,
        }
    }

    print(f"\n  ▸ Sumário {variant_name}: "
          f"{len(table_metrics)} tabelas | "
          f"{total_in} tokens entrada | "
          f"{total_out} tokens saída | "
          f"{variant_elapsed}s total")

    # salva tópicos
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(table_topics, f, ensure_ascii=False, indent=2)

    # salva métricas (sumário primeiro, depois por tabela)
    full_metrics = {**summary_block, **table_metrics}
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(full_metrics, f, ensure_ascii=False, indent=2)

    print(f"  ✓ tópicos  → {out_path}")
    print(f"  ✓ métricas → {metrics_path}")

    return table_topics, table_metrics


def main():
    client   = load_env()
    metadata = load_metadata()

    print(f"Tabelas carregadas: {len(metadata)}")
    print(f"Variantes a rodar:  {list(variants_to_run.keys())}")

    all_results = {}
    all_metrics = {}
    global_start = time.perf_counter()

    for variant_name, summarize_fn in variants_to_run.items():
        topics, metrics = run_variant(client, metadata, variant_name, summarize_fn)
        all_results[variant_name] = topics
        all_metrics[variant_name] = metrics

    # --- consolidado de tópicos ---
    consolidated_path = ABLATION_DIR / f"consolidated_{MODEL_NAME}_{RUN}.json"
    consolidated = {}
    for table_meta in metadata:
        full_name = f"{table_meta.get('schema')}.{table_meta.get('table_name')}"
        consolidated[full_name] = {
            variant: all_results[variant].get(full_name, [])
            for variant in variants_to_run
        }
    with consolidated_path.open("w", encoding="utf-8") as f:
        json.dump(consolidated, f, ensure_ascii=False, indent=2)

    # --- consolidado de métricas ---
    global_elapsed = round(time.perf_counter() - global_start, 3)

    metrics_consolidated_path = ABLATION_DIR / f"metrics_consolidated_{MODEL_NAME}_{RUN}.json"
    metrics_by_variant = {}
    for variant_name, metrics in all_metrics.items():
        summary = metrics.get("_summary", {})
        metrics_by_variant[variant_name] = {
            "total_tokens_in":  summary.get("total_tokens_in",  0),
            "total_tokens_out": summary.get("total_tokens_out", 0),
            "total_tokens":     summary.get("total_tokens",     0),
            "total_elapsed_s":  summary.get("total_elapsed_s",  0),
            "tables_processed": summary.get("tables_processed",  0),
            "per_table": {
                k: v for k, v in metrics.items() if k != "_summary"
            },
        }

    metrics_consolidated = {
        "_global_summary": {
            "total_variants":      len(variants_to_run),
            "global_elapsed_s":    global_elapsed,
            "grand_total_tokens_in":  sum(
                v["total_tokens_in"]  for v in metrics_by_variant.values()
            ),
            "grand_total_tokens_out": sum(
                v["total_tokens_out"] for v in metrics_by_variant.values()
            ),
            "grand_total_tokens": sum(
                v["total_tokens"] for v in metrics_by_variant.values()
            ),
        },
        "by_variant": metrics_by_variant,
    }

    with metrics_consolidated_path.open("w", encoding="utf-8") as f:
        json.dump(metrics_consolidated, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✓ Consolidado tópicos  → {consolidated_path}")
    print(f"✓ Consolidado métricas → {metrics_consolidated_path}")
    print(f"  Tempo total: {global_elapsed}s")
    print(f"  Tokens totais (entrada): "
          f"{metrics_consolidated['_global_summary']['grand_total_tokens_in']}")
    print(f"  Tokens totais (saída):   "
          f"{metrics_consolidated['_global_summary']['grand_total_tokens_out']}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()