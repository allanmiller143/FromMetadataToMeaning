# Relatório de Filtragem de Metadados

**Data de Execução:** 11/06/2026 21:32:32

## Resumo

- **Total de tabelas originais:** 129
- **Tabelas mantidas:** 127
- **Tabelas removidas:** 2
- **Percentual removido:** 1.55%

## Critério de Filtragem

Foram removidas **apenas** as tabelas com `row_count = 0` (tabelas vazias).

## Tabelas Removidas

Total de tabelas removidas: **2**

| Schema | Nome da Tabela | Row Count |
|--------|----------------|-----------|
| nhanes_laboratory | folfms_j | 0 |
| public | nhanes_catalog | 0 |

## Tabelas Mantidas

Total de tabelas mantidas: **127**

### Estatísticas das Tabelas Mantidas

- **Menor row_count:** 127
- **Maior row_count:** 112,683
- **Média de row_count:** 7,656.29

### Amostra das Tabelas Mantidas (primeiras 20)

| Schema | Nome da Tabela | Row Count |
|--------|----------------|-----------|
| nhanes_admin | load_catalog | 127 |
| nhanes_demographics | demo_j | 9,254 |
| nhanes_dietary | dr1iff_j | 112,683 |
| nhanes_dietary | dr1tot_j | 8,704 |
| nhanes_dietary | dr2iff_j | 93,500 |
| nhanes_dietary | dr2tot_j | 8,704 |
| nhanes_dietary | ds1ids_j | 6,068 |
| nhanes_dietary | ds1tot_j | 8,704 |
| nhanes_dietary | ds2ids_j | 5,776 |
| nhanes_dietary | ds2tot_j | 8,704 |
| nhanes_dietary | dsqids_j | 9,984 |
| nhanes_dietary | dsqtot_j | 9,254 |
| nhanes_examination | aux_j | 3,131 |
| nhanes_examination | auxar_j | 33,721 |
| nhanes_examination | auxtym_j | 5,585 |
| nhanes_examination | auxwbr_j | 5,682 |
| nhanes_examination | bmx_j | 8,704 |
| nhanes_examination | bpx_j | 8,704 |
| nhanes_examination | bpxo_j | 7,132 |
| nhanes_examination | dxx_j | 5,114 |

*... e mais 107 tabelas*

## Justificativa Científica

A remoção de tabelas com `row_count = 0` é justificada pelos seguintes motivos:

1. **Ausência de Dados:** Tabelas vazias não contêm informações que possam contribuir para a análise ou geração de insights pela LLM.

2. **Redução de Ruído:** A inclusão de metadados de tabelas vazias adiciona ruído informacional sem valor semântico ou estatístico.

3. **Otimização de Recursos:** A remoção dessas tabelas reduz o tamanho do payload enviado para a LLM, otimizando o uso de tokens e melhorando a eficiência do processamento.

4. **Foco em Dados Relevantes:** Manter apenas tabelas com dados reais permite que a LLM concentre sua análise em estruturas que efetivamente contêm informação.

---

*Relatório gerado automaticamente pelo script de filtragem de metadados.*
