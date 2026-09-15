#!/usr/bin/env python3
"""
Script para filtrar tabelas de metadados com base em critérios de row_count
E, em seguida, anonimizar automaticamente o resultado (chamando
anonymize_metadata.py), sem gravar em disco o JSON intermediário
filtrado-mas-ainda-não-anonimizado.

Pipeline (um único comando, um único arquivo de dados salvo no final):
    1) Lê o metadata.json bruto.
    2) Filtra em memória: remove APENAS tabelas com row_count igual a 0.
    3) Anonimiza em memória o resultado filtrado (usando
       anonymize_metadata.anonymize_metadata_data()).
    4) Salva SOMENTE o JSON final já filtrado E anonimizado.

O JSON de saída mantém exatamente o mesmo formato do JSON de entrada.
Este script precisa estar na mesma pasta que anonymize_metadata.py e
sensitive_columns.json.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

from anonymize_metadata import anonymize_metadata_data, generate_report as generate_anon_report

def generate_report(metadata, filtered_metadata, removed_tables, output_file: str):
    """
    Gera um relatório em Markdown com as estatísticas da filtragem.
    
    Args:
        metadata: Lista original de tabelas
        filtered_metadata: Lista filtrada de tabelas
        removed_tables: Lista de tabelas removidas
        output_file: Caminho para o arquivo de relatório
    """
    
    total_tables = len(metadata)
    filtered_count = len(filtered_metadata)
    removed_count = len(removed_tables)
    
    report = f"""# Relatório de Filtragem de Metadados

**Data de Execução:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

## Resumo

- **Total de tabelas originais:** {total_tables}
- **Tabelas mantidas:** {filtered_count}
- **Tabelas removidas:** {removed_count}
- **Percentual removido:** {(removed_count/total_tables)*100:.2f}%

## Critério de Filtragem

Foram removidas **apenas** as tabelas com `row_count = 0` (tabelas vazias).

## Tabelas Removidas

Total de tabelas removidas: **{removed_count}**

| Schema | Nome da Tabela | Row Count |
|--------|----------------|-----------|
"""
    
    # Adicionar tabelas removidas na tabela
    for table in removed_tables:
        schema = table.get('schema', 'N/A')
        table_name = table.get('table_name', 'N/A')
        row_count = table.get('row_count', 0)
        report += f"| {schema} | {table_name} | {row_count} |\n"
    
    report += f"""
## Tabelas Mantidas

Total de tabelas mantidas: **{filtered_count}**

### Estatísticas das Tabelas Mantidas

"""
    
    # Calcular estatísticas das tabelas mantidas
    if filtered_metadata:
        row_counts = [t.get('row_count', 0) for t in filtered_metadata]
        min_rows = min(row_counts)
        max_rows = max(row_counts)
        avg_rows = sum(row_counts) / len(row_counts)
        
        report += f"""- **Menor row_count:** {min_rows:,}
- **Maior row_count:** {max_rows:,}
- **Média de row_count:** {avg_rows:,.2f}

### Amostra das Tabelas Mantidas (primeiras 20)

| Schema | Nome da Tabela | Row Count |
|--------|----------------|-----------|
"""
        
        for table in filtered_metadata[:20]:
            schema = table.get('schema', 'N/A')
            table_name = table.get('table_name', 'N/A')
            row_count = table.get('row_count', 0)
            report += f"| {schema} | {table_name} | {row_count:,} |\n"
        
        if len(filtered_metadata) > 20:
            report += f"\n*... e mais {len(filtered_metadata) - 20} tabelas*\n"
    
    report += """
## Justificativa Científica

A remoção de tabelas com `row_count = 0` é justificada pelos seguintes motivos:

1. **Ausência de Dados:** Tabelas vazias não contêm informações que possam contribuir para a análise ou geração de insights pela LLM.

2. **Redução de Ruído:** A inclusão de metadados de tabelas vazias adiciona ruído informacional sem valor semântico ou estatístico.

3. **Otimização de Recursos:** A remoção dessas tabelas reduz o tamanho do payload enviado para a LLM, otimizando o uso de tokens e melhorando a eficiência do processamento.

4. **Foco em Dados Relevantes:** Manter apenas tabelas com dados reais permite que a LLM concentre sua análise em estruturas que efetivamente contêm informação.

---

*Relatório gerado automaticamente pelo script de filtragem de metadados.*
"""
    
    # Salvar relatório
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # print(f"Relatório salvo em: {output_file}")


def filter_and_anonymize(input_file: str, output_file: str, filter_report_file: str,
                         anon_report_file: str, config_file: str):
    
    with open(input_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    total_tables = len(metadata)

    # --- Etapa 1: filtragem (em memória) ---
    # COMENTADO TEMPORARIAMENTE - MANTER TODAS AS TABELAS
    # filtered_metadata = [
    #     table for table in metadata
    #     if table.get('row_count', 0) > 0
    # ]
    # 
    # removed_tables = [
    #     table for table in metadata
    #     if table.get('row_count', 0) == 0
    # ]
    
    # MANTER TODAS AS TABELAS (incluindo vazias)
    filtered_metadata = metadata
    removed_tables = []
    
    filtered_count = len(filtered_metadata)
    removed_count = len(removed_tables)

    # Relatório da filtragem
    generate_report(metadata, filtered_metadata, removed_tables, filter_report_file)

    # --- Etapa 2: anonimização ---
    anon_metadata, per_table_anonymized, per_table_content_pii, patterns, auto_anonymize_keys = \
        anonymize_metadata_data(filtered_metadata, config_file)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(anon_metadata, f, indent=2, ensure_ascii=False)

    generate_anon_report(anon_metadata, per_table_anonymized, per_table_content_pii,
                          patterns, auto_anonymize_keys, anon_report_file)

def main():
    """Função principal do script."""

    # Pasta onde este script está salvo — usada para localizar o
    # sensitive_columns.json de forma independente de onde o comando
    # for executado (mesma convenção do anonymize_metadata.py).
    SCRIPT_DIR = Path(__file__).resolve().parent

    # Configurações padrão
    input_file = "./data/magento2/step1_output/metadata.json"
    output_file = "./data/magento2/step2_output/metadata.json"
    filter_report_file = "./data/magento2/step2_output/relatorio_filtragem.md"
    anon_report_file = "./data/magento2/step2_output/relatorio_anonimizacao.md"
    config_file = str(SCRIPT_DIR / "sensitive_columns.json")

    # Verificar argumentos da linha de comando
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    if len(sys.argv) > 3:
        filter_report_file = sys.argv[3]
    if len(sys.argv) > 4:
        anon_report_file = sys.argv[4]
    if len(sys.argv) > 5:
        config_file = sys.argv[5]

    # Verificar se o arquivo de entrada existe
    if not Path(input_file).exists():
        print(f"ERRO: Arquivo de entrada não encontrado: {input_file}")
        sys.exit(1)

    if not Path(config_file).exists():
        print(f"ERRO: Arquivo de configuração não encontrado: {config_file}")
        print("Crie um sensitive_columns.json com a chave 'patterns' (lista de regex).")
        sys.exit(1)

    # Criar diretório de saída se não existir
    output_dir = Path(output_file).parent
    if output_dir and not output_dir.exists():
        print(f"Criando diretório: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)

    # Executar filtragem + anonimização em sequência
    try:
        filter_and_anonymize(input_file, output_file, filter_report_file, anon_report_file, config_file)
        print("Processo concluído com sucesso!")
        print(f"Metadata filtrado e anonimizado: {output_file}")
        print(f"Relatório de filtragem: {filter_report_file}")
        print(f"Relatório de anonimização: {anon_report_file}")
    except Exception as e:
        print(f"ERRO durante a execução: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # print("=" * 70)
    # print("Script de Filtragem de Metadados")
    # print("=" * 70)
    # print()
    # print("Uso: python filter_metadata.py [input_file] [output_file] [report_file]")
    # print()
    # print("Argumentos:")
    # print("  input_file   : Arquivo JSON de entrada")
    # print("                 (padrão: ../step1/metadata_output_advanced/metadata_advanced_consolidated.json)")
    # print("  output_file  : Arquivo JSON de saída")
    # print("                 (padrão: metadata_output_advanced/metadata_advanced_consolidated_filtered.json)")
    # print("  report_file  : Arquivo de relatório MD")
    # print("                 (padrão: metadata_output_advanced/relatorio_filtragem.md)")
    # print()
    # print("Critério: Remove APENAS tabelas com row_count = 0")
    # print()
    # print("=" * 70)
    # print()
    
    main()