"""
NHANES — Validação dos Resultados do Pipeline de Profiling
===========================================================
Gera a tabela de validação equivalente à Tabela VI do artigo WCCI,
comparando os macro-temas gerados pelo SOM com a estrutura oficial
do NHANES (componentes e nomes de arquivos do CDC).

Entradas esperadas (mesma pasta do script ou ajuste os caminhos):
  - som_macrothemes.json
  - som_cluster_temas_tabelas.csv
  - summary_consistency.csv

Saídas:
  - nhanes_validation_table.csv   → tabela fina (arquivo → macro-tema)
  - nhanes_validation_report.txt  → relatório completo com métricas

Uso:
    python nhanes_validation.py
"""

import json
import pandas as pd
from pathlib import Path

# ─────────────────────────────────────────────
#  CAMINHOS — ajuste se necessário
# ─────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
MACROTHEMES_JSON = BASE_DIR / "som_macrothemes.json"
CLUSTER_CSV      = BASE_DIR / "som_cluster_temas_tabelas.csv"
CONSISTENCY_CSV  = BASE_DIR / "summary_consistency.csv"

OUTPUT_TABLE  = BASE_DIR / "nhanes_validation_table.csv"
OUTPUT_REPORT = BASE_DIR / "nhanes_validation_report.txt"

# ─────────────────────────────────────────────
#  NOMES OFICIAIS DOS ARQUIVOS NHANES (CDC)
#  slug do banco → nome oficial do CDC
# ─────────────────────────────────────────────
OFFICIAL_FILE_NAMES = {
    # Demographics
    "demo_j":    "Demographic Variables and Sample Weights",
    # Dietary
    "dr1iff_j":  "Dietary Interview - Individual Foods (Day 1)",
    "dr1tot_j":  "Dietary Interview - Total Nutrient Intakes (Day 1)",
    "dr2iff_j":  "Dietary Interview - Individual Foods (Day 2)",
    "dr2tot_j":  "Dietary Interview - Total Nutrient Intakes (Day 2)",
    "ds1ids_j":  "Dietary Supplement Use (Day 1 - Individual)",
    "ds1tot_j":  "Dietary Supplement Use (Day 1 - Total)",
    "ds2ids_j":  "Dietary Supplement Use (Day 2 - Individual)",
    "ds2tot_j":  "Dietary Supplement Use (Day 2 - Total)",
    "dsqids_j":  "Dietary Supplement Use (30-Day - Individual)",
    "dsqtot_j":  "Dietary Supplement Use (30-Day - Total)",
    # Examination
    "aux_j":     "Audiometry",
    "auxar_j":   "Audiometry - Acoustic Reflex",
    "auxtym_j":  "Audiometry - Tympanometry",
    "auxwbr_j":  "Audiometry - Wideband Reflectance",
    "bmx_j":     "Body Measures",
    "bpx_j":     "Blood Pressure",
    "bpxo_j":    "Blood Pressure & Cholesterol",
    "dxx_j":     "DXA - Whole Body",
    "dxxag_j":   "DXA - Android/Gynoid",
    "dxxfem_j":  "DXA - Femur",
    "dxxspn_j":  "DXA - Spine",
    "lux_j":     "Lower Extremity Disease",
    "ohxden_j":  "Oral Health - Dentition",
    "ohxref_j":  "Oral Health - Recommendation of Care",
    # Laboratory
    "alb_cr_j":  "Albumin & Creatinine - Urine",
    "biopro_j":  "Standard Biochemistry Profile",
    "cbc_j":     "Complete Blood Count",
    "cmv_j":     "CMV IgG & IgM Antibodies - Serum",
    "cot_j":     "Cotinine - Serum",
    "crco_j":    "Creatinine & Cotinine - Urine",
    "ephpp_j":   "Pesticides - Environmental - Urine",
    "ethox_j":   "Glyphosate - Urine",
    "fastqx_j":  "Fasting Questionnaire",
    "fertin_j":  "Ferritin",
    "fetib_j":   "Iron, TIBC & Transferrin Saturation",
    "folate_j":  "Folate - RBC",
    "fr_j":      "Fluoride - Urine",
    "ghb_j":     "Glycohemoglobin",
    "glu_j":     "Plasma Fasting Glucose",
    "hdl_j":     "HDL Cholesterol",
    "hepa_j":    "Hepatitis A",
    "hepb_s_j":  "Hepatitis B Surface Antibody",
    "hepbd_j":   "Hepatitis B: Core Antibody & Surface Antigen",
    "hepc_j":    "Hepatitis C Antibody & RNA",
    "hepe_j":    "Hepatitis E IgG & IgM Antibodies",
    "hiv_j":     "HIV Antibody Test",
    "hscrp_j":   "High-Sensitivity C-Reactive Protein (hsCRP)",
    "ihgem_j":   "Mercury - Inorganic & Ethyl",
    "ins_j":     "Insulin",
    "opd_j":     "Organophosphate Insecticides - Urine",
    "pah_j":     "Polycyclic Aromatic Hydrocarbons - Urine",
    "pbcd_j":    "Cadmium, Lead, Mercury, Selenium & Manganese - Blood",
    "pernt_j":   "Perchlorate, Nitrate & Thiocyanate - Urine",
    "pfas_j":    "Perfluoroalkyl and Polyfluoroalkyl Substances (PFAS)",
    "phthte_j":  "Phthalates & Plasticizers Metabolites - Urine",
    "ssagp_j":   "Alpha-1-Acid Glycoprotein - Serum (Surplus)",
    "ssfr_j":    "Flame Retardants & Plasticizers - Serum (Surplus)",
    "ssglyp_j":  "Glyphosate - Urine (Surplus)",
    "ssneon_j":  "Neonicotinoid Insecticides & Metabolites - Urine (Surplus)",
    "sspfas_j":  "PFAS (Surplus)",
    "sstst_j":   "Sex Steroid Hormone Panel (Surplus)",
    "ssuvcm_j":  "Urinary VOC Metabolites (Surplus)",
    "ssuvoc_j":  "Volatile Organic Compounds - Blood (Surplus)",
    "tchol_j":   "Total Cholesterol",
    "tfr_j":     "Transferrin Receptor",
    "trigly_j":  "Triglycerides & LDL-Cholesterol",
    "uas_j":     "Arsenics - Urine",
    "ucflow_j":  "Urine Collection - Volume & Flow Rate",
    "ucm_j":     "Mercury - Urine",
    "ucot_j":    "Cotinine & Hydroxycotinine - Urine",
    "ucpreg_j":  "Urine Pregnancy Test",
    "uhg_j":     "Mercury - Urine (Surplus)",
    "uio_j":     "Iodine - Urine",
    "um_j":      "Metals - Urine",
    "uni_j":     "Nitrate & Nitrite - Urine",
    "uphopm_j":  "Organophosphate Insecticides - Urine (Surplus)",
    "utas_j":    "Total Arsenic & Speciated Arsenics - Urine (Surplus)",
    "uvoc_j":    "Volatile Organic Compounds - Blood",
    "vic_j":     "Vitamin C",
    "vid_j":     "Vitamin D",
    "vitaec_j":  "Vitamin A, E & Carotenoids",
    "vocwb_j":   "Volatile Organic Compounds - Water/Blood",
    # Questionnaire
    "acq_j":     "Acculturation",
    "alq_j":     "Alcohol Use",
    "auq_j":     "Audiometry (Questionnaire)",
    "bpq_j":     "Blood Pressure & Cholesterol (Questionnaire)",
    "cbq_j":     "Consumer Behavior",
    "cbqpfa_j":  "Consumer Behavior Phone Follow-Up - Adults",
    "cbqpfc_j":  "Consumer Behavior Phone Follow-Up - Children",
    "cdq_j":     "Cardiovascular Health",
    "dbq_j":     "Diet Behavior & Nutrition",
    "deq_j":     "Dermatology",
    "diq_j":     "Diabetes",
    "dlq_j":     "Disability",
    "dpq_j":     "Mental Health - Depression Screener",
    "duq_j":     "Drug Use",
    "ecq_j":     "Early Childhood",
    "fsq_j":     "Food Security",
    "heq_j":     "Hepatitis (Questionnaire)",
    "hiq_j":     "Health Insurance",
    "hoq_j":     "Housing Characteristics",
    "hsq_j":     "Current Health Status",
    "huq_j":     "Hospital Utilization & Access to Care",
    "imq_j":     "Immunization",
    "inq_j":     "Income",
    "kiq_u_j":   "Kidney Conditions - Urology",
    "mcq_j":     "Medical Conditions",
    "ocq_j":     "Occupation",
    "ohq_j":     "Oral Health (Questionnaire)",
    "osq_j":     "Osteoporosis",
    "paq_j":     "Physical Activity",
    "paqy_j":    "Physical Activity - Youth",
    "pfq_j":     "Physical Functioning",
    "puqmec_j":  "Pesticide Use",
    "rhq_j":     "Reproductive Health",
    "rxq_rx_j":  "Prescription Medications",
    "rxqasa_j":  "Aspirin Use",
    "slq_j":     "Sleep Disorders",
    "smq_j":     "Smoking - Cigarette Use",
    "smqfam_j":  "Smoking - Household Smokers",
    "smqrtu_j":  "Smoking - Recent Tobacco Use",
    "smqshs_j":  "Smoking - Secondhand Smoke Exposure",
    "vtq_j":     "Volatile Toxicant",
    "whq_j":     "Weight History",
    "whqmec_j":  "Weight History - Youth",
}

# ─────────────────────────────────────────────
#  ALINHAMENTO ESPERADO por componente
#  (macro-temas do SOM considerados semanticamente
#   corretos para cada componente oficial)
# ─────────────────────────────────────────────
EXPECTED_ALIGNMENT = {
    "Demographics": [
        "perfil demografico", "condicao de moradia", "pesos amostrais",
        "catalogo de dados de pesquisa", "genero", "idade de inicio",
    ],
    "Dietary": [
        "ingestao de nutrientes por suplemento", "suplementos dieteticos",
        "consumo de nutrientes", "frequencia de consumo alimentar",
        "analise de dieta", "composicao de alimentos",
        "composicao nutricional de suplementos", "pesos dieteticos",
        "pesquisa de dieta alimentar", "padroes consumo alimentar",
        "status nutricional de iodo",
    ],
    "Examination": [
        "status de saude", "medidas de peso corporal", "condicao dentaria",
        "pressao arterial", "densidade ossea", "exame auditivo",
        "avaliacao de composicao corporal", "dados antropometricos",
        "circunferencias corporais", "distribuicao de gordura",
        "status de exame", "resultados de exames", "limiar auditivo",
    ],
    "Laboratory": [
        "pesquisa laboratorial", "analise de urina", "analise de biomarcadores",
        "hepatite b sorologia", "controle glicemico", "analise de hemograma",
        "analise de dados laboratoriais", "exposicao a fenois",
        "analise de substancias quimicas", "colesterol total",
        "niveis de glicose", "marcadores laboratoriais", "saude geral",
        "valores laboratoriais", "resultados de exames",
        "medidas laboratoriais de lipidios", "marcadores inflamatorios",
        "biomonitoramento de contaminantes", "exposicao a contaminantes",
        "analise de triglicerideos", "prevalencia de anticorpos",
    ],
    "Questionnaire": [
        "questionario de saude", "respostas de questionario de saude",
        "avaliacao sintomas depressivos", "habitos de tabagismo",
        "tempo de atividade diaria", "uso de medicamentos",
        "frequencia de atividade fisica", "status de saude",
        "avaliacao de saude", "condicao dentaria", "qualidade de vida",
        "saude geral", "densidade ossea", "condicoes medicas",
        "historico de gravidez", "padroes alimentares",
    ],
}

# ─────────────────────────────────────────────
#  REFERÊNCIA E-SUS (para comparativo)
# ─────────────────────────────────────────────
ESUS_METRICS = {
    "n_tables": 885,
    "n_macrothemes": 254,
    "som_grid": "18x16",
    "qe": 0.694,
    "te": 0.077,
    "score": 0.766,
    "intra_soft_dice_best": 0.951,   # OpenAI
    "inter_soft_dice_mean": 0.710,
    "official_coverage": 12/14,      # 85.7%
}

# ─────────────────────────────────────────────
#  FUNÇÕES
# ─────────────────────────────────────────────

def load_data():
    with open(MACROTHEMES_JSON, encoding="utf-8") as f:
        macrothemes = json.load(f)
    df_cluster = pd.read_csv(CLUSTER_CSV)
    df_consistency = pd.read_csv(CONSISTENCY_CSV)
    return macrothemes, df_cluster, df_consistency


def build_rankings(macrothemes):
    sorted_mt = sorted(macrothemes, key=lambda x: x["frequencia_total"], reverse=True)
    rank  = {d["macrotema"]: i + 1 for i, d in enumerate(sorted_mt)}
    freq  = {d["macrotema"]: d["frequencia_total"] for d in macrothemes}
    nsub  = {d["macrotema"]: d["num_subtemas"] for d in macrothemes}
    return rank, freq, nsub


def map_table_to_primary_macro(df_cluster):
    """Retorna {tabela: (macrotema_primario, frequencia)}."""
    table_to_macro = {}
    for _, row in df_cluster.iterrows():
        for tab in str(row["Tabelas de Origem"]).split(";"):
            tab = tab.strip()
            if not tab or "nhanes_admin" in tab:
                continue
            cur = table_to_macro.get(tab)
            if cur is None or row["Frequência"] > cur[1]:
                table_to_macro[tab] = (row["Macrotema"], row["Frequência"])
    return table_to_macro


def build_validation_table(table_to_macro, macro_rank, macro_freq):
    rows = []
    for tab, (macro, _) in sorted(table_to_macro.items()):
        slug    = tab.split(".")[-1]
        comp    = tab.split(".")[0].replace("nhanes_", "").capitalize()
        official = OFFICIAL_FILE_NAMES.get(slug, f"[{slug.upper()} — adicione em OFFICIAL_FILE_NAMES]")
        rows.append({
            "Component":           comp,
            "NHANES Official File": official,
            "SOM Macro-Theme":     macro,
            "Rank":                macro_rank.get(macro, "?"),
            "Theme Frequency":     macro_freq.get(macro, "?"),
        })
    return pd.DataFrame(rows)


def compute_coverage(result):
    """Calcula métricas de cobertura semântica por componente."""
    metrics = {}
    total_aligned = 0
    for comp, expected in EXPECTED_ALIGNMENT.items():
        sub     = result[result["Component"] == comp]
        aligned = sub[sub["SOM Macro-Theme"].isin(expected)]
        metrics[comp] = {
            "total":   len(sub),
            "aligned": len(aligned),
            "pct":     len(aligned) / len(sub) * 100 if len(sub) > 0 else 0,
        }
        total_aligned += len(aligned)
    metrics["TOTAL"] = {
        "total":   len(result),
        "aligned": total_aligned,
        "pct":     total_aligned / len(result) * 100,
    }
    return metrics


def print_and_save_report(result, coverage, df_consistency, macrothemes,
                          macro_rank, macro_freq):
    lines = []
    sep = "=" * 65

    lines += [sep, "NHANES — VALIDAÇÃO DO PIPELINE DE PROFILING TEMÁTICO", sep, ""]

    # ── Tabela de validação fina ──────────────────────────────────
    lines += ["TABLE: NHANES Official File  →  SOM Macro-Theme", "-" * 65]
    prev_comp = None
    for _, row in result.iterrows():
        if row["Component"] != prev_comp:
            lines.append(f"\n  [{row['Component'].upper()}]")
            prev_comp = row["Component"]
        lines.append(
            f"    {row['NHANES Official File']:<48} "
            f"→  {row['SOM Macro-Theme']}  (#{row['Rank']})"
        )

    # ── Cobertura por componente ──────────────────────────────────
    lines += ["", sep, "COBERTURA SEMÂNTICA POR COMPONENTE", "-" * 65]
    for comp, m in coverage.items():
        bar = "█" * int(m["pct"] / 5)
        lines.append(f"  {comp:<15} {m['aligned']:>3}/{m['total']:<3}  {m['pct']:5.1f}%  {bar}")

    # ── Consistência ─────────────────────────────────────────────
    lines += ["", sep, "CONSISTÊNCIA INTRA / INTER-MODELO", "-" * 65]
    intra = df_consistency[df_consistency["Tipo"] == "INTRA"]
    inter = df_consistency[df_consistency["Tipo"] == "INTER"]

    lines.append("  Intra-model (Hard Dice / Soft Dice):")
    for _, r in intra.iterrows():
        lines.append(
            f"    {r['Alvo']:<12}  Hard={r['HardDice_Lex_mean']:.3f}  "
            f"Soft={r['SoftDice_Sem_mean']:.3f}"
        )

    lines.append("\n  Inter-model (Hard Dice / Soft Dice):")
    for _, r in inter.iterrows():
        lines.append(
            f"    {r['Alvo']:<30}  Hard={r['HardDice_Lex_mean']:.3f}  "
            f"Soft={r['SoftDice_Sem_mean']:.3f}"
        )

    # ── Top-10 macro-temas ────────────────────────────────────────
    lines += ["", sep, "TOP-10 MACRO-TEMAS POR FREQUÊNCIA", "-" * 65]
    top10 = sorted(macrothemes, key=lambda x: x["frequencia_total"], reverse=True)[:10]
    for i, d in enumerate(top10, 1):
        lines.append(
            f"  {i:>2}. {d['macrotema']:<40} "
            f"freq={d['frequencia_total']:>4}  subtemas={d['num_subtemas']}"
        )

    # ── Comparativo E-SUS vs NHANES ───────────────────────────────
    lines += ["", sep, "COMPARATIVO E-SUS vs NHANES", "-" * 65]
    n_tables  = coverage["TOTAL"]["total"]
    n_mt      = len(macrothemes)
    best_intra = intra["SoftDice_Sem_mean"].max()
    mean_inter = inter["SoftDice_Sem_mean"].mean()
    cov_pct    = coverage["TOTAL"]["pct"]

    lines += [
        f"  {'Métrica':<30} {'E-SUS':>10} {'NHANES':>10}",
        f"  {'-'*50}",
        f"  {'Tabelas':<30} {ESUS_METRICS['n_tables']:>10} {n_tables:>10}",
        f"  {'Macro-temas gerados':<30} {ESUS_METRICS['n_macrothemes']:>10} {n_mt:>10}",
        f"  {'SOM Grid':<30} {ESUS_METRICS['som_grid']:>10} {'14x14':>10}",
        f"  {'SOM Score (QE+TE) ↓':<30} {ESUS_METRICS['score']:>10.3f} {0.649:>10.3f}",
        f"  {'Topographic Error (TE) ↓':<30} {ESUS_METRICS['te']:>10.3f} {0.015:>10.3f}",
        f"  {'Intra Soft Dice (melhor) ↑':<30} {ESUS_METRICS['intra_soft_dice_best']:>10.3f} {best_intra:>10.3f}",
        f"  {'Inter Soft Dice (média) ↑':<30} {ESUS_METRICS['inter_soft_dice_mean']:>10.3f} {mean_inter:>10.3f}",
        f"  {'Cobertura semântica ↑':<30} {'85.7%':>10} {cov_pct:>9.1f}%",
    ]

    lines += ["", sep]

    report = "\n".join(lines)
    print(report)

    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nRelatório salvo em: {OUTPUT_REPORT}")


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main():
    print("Carregando dados...")
    macrothemes, df_cluster, df_consistency = load_data()

    macro_rank, macro_freq, macro_nsub = build_rankings(macrothemes)
    table_to_macro = map_table_to_primary_macro(df_cluster)

    print(f"  {len(table_to_macro)} tabelas mapeadas | {len(macrothemes)} macro-temas")

    result = build_validation_table(table_to_macro, macro_rank, macro_freq)
    result.to_csv(OUTPUT_TABLE, index=False, encoding="utf-8-sig")
    print(f"  Tabela de validação salva em: {OUTPUT_TABLE}")

    coverage = compute_coverage(result)

    print_and_save_report(
        result, coverage, df_consistency, macrothemes, macro_rank, macro_freq
    )


if __name__ == "__main__":
    main()