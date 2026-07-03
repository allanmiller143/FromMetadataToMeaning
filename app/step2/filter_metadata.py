#!/usr/bin/env python3
"""
Script para filtrar tabelas de metadados com base em critérios de row_count.

Critérios de filtragem:
- Remove APENAS tabelas com row_count igual a 0

O JSON de saída mantém exatamente o mesmo formato do JSON de entrada.
"""

import json
import sys
from pathlib import Path
from datetime import datetime


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


def filter_metadata(input_file: str, output_file: str, report_file: str):
    """
    Filtra tabelas de metadados baseado no row_count.
    Remove APENAS tabelas com row_count = 0.
    
    Args:
        input_file: Caminho para o arquivo JSON de entrada
        output_file: Caminho para o arquivo JSON de saída
        report_file: Caminho para o arquivo de relatório MD
    """
    
    # Ler o arquivo JSON de entrada
    # print(f"Lendo arquivo: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    total_tables = len(metadata)
    # print(f"Total de tabelas no arquivo original: {total_tables}")
    
    # Filtrar tabelas com row_count > 0
    filtered_metadata = [
        table for table in metadata 
        if table.get('row_count', 0) > 0
    ]
    
    # Tabelas removidas (row_count = 0)
    removed_tables = [
        table for table in metadata 
        if table.get('row_count', 0) == 0
    ]
    
    filtered_count = len(filtered_metadata)
    removed_count = len(removed_tables)
    
    # print(f"\nTabelas removidas (row_count = 0): {removed_count}")
    # print(f"Tabelas mantidas: {filtered_count}")
    # print(f"Percentual removido: {(removed_count/total_tables)*100:.2f}%")
    
    # Mostrar algumas tabelas removidas
    # if removed_tables:
    #     print(f"\nExemplos de tabelas removidas:")
    #     for table in removed_tables[:10]:
    #         print(f"  - {table['table_name']}: {table['row_count']} linhas")
    #     if len(removed_tables) > 10:
    #         print(f"  ... e mais {len(removed_tables) - 10} tabelas")
    
    # Salvar o JSON filtrado mantendo o formato original
    # print(f"\nSalvando arquivo filtrado: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_metadata, f, indent=2, ensure_ascii=False)
    
    # Gerar relatório
    # print(f"\nGerando relatório...")
    generate_report(metadata, filtered_metadata, removed_tables, report_file)
    
    # print("\nProcesso concluído com sucesso!")


def main():
    """Função principal do script."""
    
    # Configurações padrão
    input_file = "./data/teixeira/step1_output/metadata.json"
    output_file = "./data/teixeira/step2_output/metadata.json"
    report_file = "./data/teixeira/step2_output/relatorio_filtragem.md"
    
    # Verificar argumentos da linha de comando
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    if len(sys.argv) > 3:
        report_file = sys.argv[3]
    
    # Verificar se o arquivo de entrada existe
    if not Path(input_file).exists():
        print(f"ERRO: Arquivo de entrada não encontrado: {input_file}")
        sys.exit(1)
    
    # Criar diretório de saída se não existir
    output_dir = Path(output_file).parent
    if output_dir and not output_dir.exists():
        print(f"Criando diretório: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Executar filtragem
    try:
        filter_metadata(input_file, output_file, report_file)
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