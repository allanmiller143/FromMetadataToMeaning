# Relatório de Filtragem de Metadados

**Data de Execução:** 03/07/2026 08:01:36

## Resumo

- **Total de tabelas originais:** 2
- **Tabelas mantidas:** 2
- **Tabelas removidas:** 0
- **Percentual removido:** 0.00%

## Critério de Filtragem

Foram removidas **apenas** as tabelas com `row_count = 0` (tabelas vazias).

## Tabelas Removidas

Total de tabelas removidas: **0**

| Schema | Nome da Tabela | Row Count |
|--------|----------------|-----------|

## Tabelas Mantidas

Total de tabelas mantidas: **2**

### Estatísticas das Tabelas Mantidas

- **Menor row_count:** 127
- **Maior row_count:** 9,254
- **Média de row_count:** 4,690.50

### Amostra das Tabelas Mantidas (primeiras 20)

| Schema | Nome da Tabela | Row Count |
|--------|----------------|-----------|
| nhanes_admin | load_catalog | 127 |
| nhanes_demographics | demo_j | 9,254 |

## Justificativa Científica

A remoção de tabelas com `row_count = 0` é justificada pelos seguintes motivos:

1. **Ausência de Dados:** Tabelas vazias não contêm informações que possam contribuir para a análise ou geração de insights pela LLM.

2. **Redução de Ruído:** A inclusão de metadados de tabelas vazias adiciona ruído informacional sem valor semântico ou estatístico.

3. **Otimização de Recursos:** A remoção dessas tabelas reduz o tamanho do payload enviado para a LLM, otimizando o uso de tokens e melhorando a eficiência do processamento.

4. **Foco em Dados Relevantes:** Manter apenas tabelas com dados reais permite que a LLM concentre sua análise em estruturas que efetivamente contêm informação.

---

*Relatório gerado automaticamente pelo script de filtragem de metadados.*
