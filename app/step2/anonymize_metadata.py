#!/usr/bin/env python3
"""
Script para anonimizar VALORES de colunas sensíveis em arquivos de metadados
(saída do extract_metadata.py), antes de enviar o JSON para uma LLM.

Diferente de simplesmente remover as colunas, este script MANTÉM a coluna
(nome, tipo, nullable etc.) e substitui apenas os VALORES REAIS por
"<anonimizado>", nos três lugares onde o extract_metadata.py grava dados
reais de amostra:

    - columns[].stats.sample_values
    - columns[].stats.frequent_values[].value
    - sample_rows[][<coluna_sensivel>]

A decisão de quais colunas são sensíveis é feita por uma lista de padrões
(regex) carregada de um arquivo JSON externo (por padrão: sensitive_columns.json),
o que torna o script reutilizável para QUALQUER base de dados, não apenas
e-SUS: basta editar esse arquivo de configuração, sem tocar no código.

O JSON de saída mantém exatamente o mesmo formato/estrutura do JSON de entrada.
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime

ANON_TOKEN = "<anonimizado>"
PII_TOKEN = "<pii_removido>"

# Trechos que indicam um tipo de coluna "numérico" (chave substituta/sequencial).
# Se o tipo NÃO contiver nenhum desses trechos, a coluna é candidata a
# "chave natural" (ex.: CPF/CNS usado como PK) quando for PK ou FK.
NUMERIC_TYPE_HINTS = ["int", "serial", "bigint", "smallint", "float", "double", "real"]

# Rede de segurança: padrões de PII procurados dentro de QUALQUER valor de
# texto, independente do nome da coluna. Cobre casos em que um dado sensível
# está embutido em texto livre (atestados, laudos) ou em blobs JSON
# serializados como string, em colunas cujo nome não denuncia o conteúdo.
CONTENT_PII_PATTERNS = [
    ("CPF/CNS", re.compile(r"\b\d{11}\b|\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")),
    ("CNS", re.compile(r"\b\d{15}\b")),
    ("EMAIL", re.compile(r"[\w\.\-]+@[\w\.\-]+\.\w+")),
]


def scrub_content_pii(text: str) -> tuple:
    """
    Procura padrões de PII (CPF/CNS/e-mail) DENTRO de um texto livre e
    substitui apenas o trecho encontrado, preservando o resto do texto.

    Isso é uma camada extra além da anonimização por nome de coluna: cobre
    o caso de campos narrativos/blob (ex.: atestado médico em texto corrido,
    ou um JSON serializado como string) que contêm dado sensível embutido,
    mesmo quando o nome da coluna não indica isso.

    NÃO substitui nomes de pessoas dentro do texto (não há um padrão regex
    confiável para isso) — por isso colunas claramente narrativas devem
    continuar cobertas pelos padrões de nome (ex.: "atestado", "laudo").

    Returns:
        (texto_com_pii_removido, houve_alteracao: bool)
    """
    if not isinstance(text, str) or not text:
        return text, False

    changed = False
    for _label, pattern in CONTENT_PII_PATTERNS:
        new_text, n = pattern.subn(PII_TOKEN, text)
        if n > 0:
            text = new_text
            changed = True
    return text, changed



# =========================================================
# Carregamento da configuração de colunas sensíveis
# =========================================================
def load_config(config_file: str):
    """
    Carrega a configuração completa (padrões + política de chaves).

    Args:
        config_file: Caminho para o JSON de configuração

    Returns:
        (patterns_compilados, auto_anonymize_non_numeric_keys: bool)
    """
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    raw_patterns = config.get("patterns", [])
    compiled = []
    for p in raw_patterns:
        try:
            compiled.append(re.compile(p, re.IGNORECASE))
        except re.error as e:
            print(f"AVISO: padrão inválido ignorado '{p}': {e}")

    auto_anonymize_keys = bool(config.get("auto_anonymize_non_numeric_keys", False))

    return compiled, auto_anonymize_keys


def is_sensitive_column(column_name: str, patterns) -> bool:
    """Verifica se o nome de uma coluna bate com algum padrão sensível."""
    return any(p.search(column_name) for p in patterns)


def looks_numeric_type(type_str: str) -> bool:
    """Verifica se uma string de tipo de coluna parece um tipo numérico/sequencial."""
    type_upper = (type_str or "").upper()
    return any(hint.upper() in type_upper for hint in NUMERIC_TYPE_HINTS)


def get_key_column_names(table: dict) -> set:
    """
    Retorna o conjunto de nomes de coluna que são Primary Key ou fazem
    parte de alguma Foreign Key da tabela.
    """
    key_columns = set()

    pk = table.get("primary_key", [])
    if isinstance(pk, list):
        key_columns.update(pk)

    fks = table.get("foreign_keys", [])
    if isinstance(fks, list):
        for fk in fks:
            if isinstance(fk, dict):
                key_columns.update(fk.get("constrained_columns", []) or [])

    return key_columns


# =========================================================
# Anonimização de uma tabela
# =========================================================
def anonymize_table(table: dict, patterns, auto_anonymize_keys: bool) -> tuple[dict, list[tuple], list[str]]:
    """
    Anonimiza os valores das colunas sensíveis de UMA tabela de metadados.

    Uma coluna é considerada sensível se:
      1) seu nome bater com algum padrão de "patterns"; OU
      2) auto_anonymize_keys=True e ela for PK/FK com tipo não-numérico
         (candidata a chave natural, ex.: CPF/CNS usado como PK).

    Colunas NÃO marcadas como sensíveis ainda passam por uma varredura de
    conteúdo (scrub_content_pii) como rede de segurança, para o caso de
    PII embutida em texto livre/blob cujo nome de coluna não denuncia.

    Args:
        table: dicionário da tabela (um item da lista do metadata.json)
        patterns: lista de regex compilados
        auto_anonymize_keys: se True, aplica a regra (2) acima

    Returns:
        (tabela_anonimizada, lista_de_(coluna, motivo)_anonimizadas,
         lista_de_colunas_com_pii_de_conteudo_removido)
    """
    anonymized_columns = []
    content_pii_columns = []

    columns = table.get("columns", [])
    sensitive_names = set()

    key_column_names = get_key_column_names(table) if auto_anonymize_keys else set()

    for col in columns:
        col_name = col.get("name", "")
        col_type = col.get("type", "")

        reason = None
        if is_sensitive_column(col_name, patterns):
            reason = "padrão de nome"
        elif col_name in key_column_names and not looks_numeric_type(col_type):
            reason = "PK/FK com tipo não-numérico (possível chave natural)"

        stats = col.get("stats")

        if reason is not None:
            sensitive_names.add(col_name)
            anonymized_columns.append((col_name, reason))

            if isinstance(stats, dict):
                if "sample_values" in stats and isinstance(stats["sample_values"], list):
                    stats["sample_values"] = [ANON_TOKEN for _ in stats["sample_values"]]

                if "frequent_values" in stats and isinstance(stats["frequent_values"], list):
                    for fv in stats["frequent_values"]:
                        if isinstance(fv, dict) and "value" in fv:
                            fv["value"] = ANON_TOKEN
            continue

        # Coluna não marcada como sensível pelo nome: rede de segurança por conteúdo.
        col_had_pii = False
        if isinstance(stats, dict):
            if "sample_values" in stats and isinstance(stats["sample_values"], list):
                new_vals = []
                for v in stats["sample_values"]:
                    new_v, changed = scrub_content_pii(v)
                    new_vals.append(new_v)
                    col_had_pii = col_had_pii or changed
                stats["sample_values"] = new_vals

            if "frequent_values" in stats and isinstance(stats["frequent_values"], list):
                for fv in stats["frequent_values"]:
                    if isinstance(fv, dict) and "value" in fv:
                        new_v, changed = scrub_content_pii(fv["value"])
                        fv["value"] = new_v
                        col_had_pii = col_had_pii or changed

        if col_had_pii:
            content_pii_columns.append(col_name)

    # sample_rows: cada linha é um dict {coluna: valor}
    sample_rows = table.get("sample_rows", [])
    if isinstance(sample_rows, list):
        for row in sample_rows:
            if not isinstance(row, dict):
                continue
            for col_name in list(row.keys()):
                if col_name in sensitive_names:
                    row[col_name] = ANON_TOKEN
                else:
                    new_v, changed = scrub_content_pii(row[col_name])
                    if changed:
                        row[col_name] = new_v
                        if col_name not in content_pii_columns:
                            content_pii_columns.append(col_name)

    return table, anonymized_columns, content_pii_columns


# =========================================================
# Relatório
# =========================================================
def generate_report(metadata, per_table_anonymized: dict, per_table_content_pii: dict, patterns, auto_anonymize_keys: bool, output_file: str):
    """
    Gera um relatório em Markdown com as estatísticas da anonimização.

    Args:
        metadata: lista de tabelas (já anonimizada)
        per_table_anonymized: dict {"schema.tabela": [(coluna, motivo), ...]}
        patterns: lista de regex usados
        auto_anonymize_keys: se a regra de PK/FK não-numérica estava ativa
        output_file: caminho do relatório MD
    """
    total_tables = len(metadata)
    tables_with_sensitive = sum(1 for cols in per_table_anonymized.values() if cols)
    total_sensitive_columns = sum(len(cols) for cols in per_table_anonymized.values())

    key_based = [
        (table_key, col_name)
        for table_key, cols in per_table_anonymized.items()
        for col_name, reason in cols
        if "chave natural" in reason
    ]

    # Conta ocorrências por nome de coluna (mesmo nome pode repetir em várias tabelas)
    column_occurrences = {}
    for cols in per_table_anonymized.values():
        for c, _reason in cols:
            column_occurrences[c] = column_occurrences.get(c, 0) + 1

    report = f"""# Relatório de Anonimização de Metadados

**Data de Execução:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

## Resumo

- **Total de tabelas processadas:** {total_tables}
- **Tabelas com colunas sensíveis:** {tables_with_sensitive}
- **Total de colunas anonimizadas (contando repetições entre tabelas):** {total_sensitive_columns}
- **Padrões de sensibilidade configurados:** {len(patterns)}
- **Detecção automática de chaves naturais (PK/FK não-numéricas):** {"ativada" if auto_anonymize_keys else "desativada"}
- **Colunas anonimizadas por serem chave natural (não pelo nome):** {len(key_based)}

## Como funciona

As colunas cujo **nome** bateu com algum padrão de sensibilidade foram mantidas
na estrutura do JSON (nome, tipo, nullable), porém todos os seus **valores**
(`stats.sample_values`, `stats.frequent_values` e `sample_rows`) foram
substituídos pelo token `{ANON_TOKEN}`.

Além dos padrões de nome, colunas que são **Primary Key ou Foreign Key** e têm
tipo **não-numérico** (varchar/text/char, em vez de int/serial/bigint) também
foram anonimizadas automaticamente — isso cobre o caso de sistemas legados
(comum no e-SUS) onde a própria chave primária/estrangeira é um dado como
CPF ou CNS. Chaves numéricas (ids sequenciais) foram mantidas intactas,
pois normalmente não identificam ninguém sozinhas e são necessárias para o
LLM entender os relacionamentos entre as tabelas.

## Chaves Anonimizadas por Serem Não-Numéricas (revise com atenção)

"""

    if key_based:
        report += "| Tabela | Coluna |\n|--------|--------|\n"
        for table_key, col_name in key_based:
            report += f"| {table_key} | {col_name} |\n"
    else:
        report += "*Nenhuma PK/FK não-numérica encontrada.*\n"

    report += """
## Colunas Sensíveis Detectadas (nomes distintos)

| Nome da Coluna | Nº de tabelas em que apareceu |
|----------------|-------------------------------|
"""

    for col_name, count in sorted(column_occurrences.items(), key=lambda x: -x[1]):
        report += f"| {col_name} | {count} |\n"

    report += """
## Detalhe por Tabela

| Tabela | Colunas Anonimizadas (motivo) |
|--------|-------------------------------|
"""

    for table_key, cols in sorted(per_table_anonymized.items()):
        cols_str = ", ".join(f"{c} ({r})" for c, r in cols) if cols else "-"
        report += f"| {table_key} | {cols_str} |\n"

    total_content_pii_cols = sum(len(v) for v in per_table_content_pii.values())
    report += f"""

## PII Encontrada DENTRO de Texto Livre / Colunas Não Marcadas pelo Nome (revise com atenção)

Estas colunas **não** bateram com nenhum padrão de nome sensível, mas continham
CPF, CNS ou e-mail *embutidos* no valor (ex.: um atestado em texto corrido, ou
um JSON serializado como string). Apenas o trecho encontrado foi substituído
por `{PII_TOKEN}` — o resto do texto original foi mantido.

**IMPORTANTE:** esta varredura reconhece apenas padrões numéricos
(CPF/CNS) e e-mail. Ela **não** identifica nomes de pessoas dentro de texto
livre, pois não existe um padrão confiável para isso. Se alguma das colunas
abaixo for um campo narrativo (atestado, laudo, observação clínica etc.),
o ideal é adicionar o nome dela em `sensitive_columns.json` para que a
coluna INTEIRA seja anonimizada, em vez de depender só desta rede de segurança.

Total de colunas com PII de conteúdo detectada: **{total_content_pii_cols}**

| Tabela | Colunas com PII embutida |
|--------|---------------------------|
"""
    if per_table_content_pii:
        for table_key, cols in sorted(per_table_content_pii.items()):
            report += f"| {table_key} | {', '.join(cols)} |\n"
    else:
        report += "*Nenhuma ocorrência.*\n"

    report += f"""

## Justificativa

Dados de saúde (como os do e-SUS) frequentemente contêm identificadores
diretos (CPF, CNS, nome) e quase-identificadores (endereço, data de
nascimento, telefone) que não podem ser enviados a serviços de LLM externos.
Em vez de remover a coluna (o que perde a informação estrutural sobre a
existência do campo, útil para o LLM entender o schema), o valor é
substituído por `{ANON_TOKEN}`, preservando a estrutura da tabela sem expor
dado real.

---

*Relatório gerado automaticamente pelo script de anonimização de metadados.*
"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)


# =========================================================
# Pipeline principal
# =========================================================
def anonymize_metadata_data(metadata: list, config_file: str):
    """
    Anonimiza uma lista de metadados JÁ CARREGADA EM MEMÓRIA (não lê nem
    escreve nenhum arquivo de dados). Permite encadear este passo depois
    de outro script (ex.: filter_metadata.py) sem precisar gravar um
    JSON intermediário em disco.

    Args:
        metadata: lista de tabelas (mesmo formato do metadata.json)
        config_file: caminho para o sensitive_columns.json

    Returns:
        (metadata_anonimizado, per_table_anonymized, per_table_content_pii,
         patterns, auto_anonymize_keys)
        — os últimos 4 valores são exatamente o que generate_report() espera.
    """
    patterns, auto_anonymize_keys = load_config(config_file)

    per_table_anonymized = {}
    per_table_content_pii = {}

    for table in metadata:
        schema = table.get("schema", "N/A")
        table_name = table.get("table_name", "N/A")
        key = f"{schema}.{table_name}"

        _, anonymized_cols, content_pii_cols = anonymize_table(table, patterns, auto_anonymize_keys)
        per_table_anonymized[key] = anonymized_cols
        if content_pii_cols:
            per_table_content_pii[key] = content_pii_cols

    return metadata, per_table_anonymized, per_table_content_pii, patterns, auto_anonymize_keys


def anonymize_metadata(input_file: str, output_file: str, report_file: str, config_file: str):
    """
    Lê o metadata.json, anonimiza valores de colunas sensíveis e salva
    o JSON anonimizado + relatório, mantendo o formato original.

    (Wrapper de anonymize_metadata_data() que lê o input de um arquivo —
    mantido para uso standalone deste script, via linha de comando.)
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    metadata, per_table_anonymized, per_table_content_pii, patterns, auto_anonymize_keys = \
        anonymize_metadata_data(metadata, config_file)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    generate_report(metadata, per_table_anonymized, per_table_content_pii, patterns, auto_anonymize_keys, report_file)


def main():
    """Função principal do script."""

    # Pasta onde este script está salvo — usada para localizar o
    # sensitive_columns.json de forma independente de onde o comando
    # for executado (evita depender do diretório de trabalho atual).
    SCRIPT_DIR = Path(__file__).resolve().parent

    # Configurações padrão (mesma convenção de pastas do filter_metadata.py)
    input_file = "./data/teixeira/step1_output/metadata.json"
    output_file = "./data/teixeira/step2_output/metadata_anonimizado.json"
    report_file = "./data/teixeira/step2_output/relatorio_anonimizacao.md"
    config_file = str(SCRIPT_DIR / "sensitive_columns.json")

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    if len(sys.argv) > 3:
        report_file = sys.argv[3]
    if len(sys.argv) > 4:
        config_file = sys.argv[4]

    if not Path(input_file).exists():
        print(f"ERRO: Arquivo de entrada não encontrado: {input_file}")
        sys.exit(1)

    if not Path(config_file).exists():
        print(f"ERRO: Arquivo de configuração não encontrado: {config_file}")
        print("Crie um sensitive_columns.json com a chave 'patterns' (lista de regex).")
        sys.exit(1)

    output_dir = Path(output_file).parent
    if output_dir and not output_dir.exists():
        print(f"Criando diretório: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

    try:
        anonymize_metadata(input_file, output_file, report_file, config_file)
        print("Processo concluído com sucesso!")
        print(f"Metadata anonimizado: {output_file}")
        print(f"Relatório: {report_file}")
    except Exception as e:
        print(f"ERRO durante a execução: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()