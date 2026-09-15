# Relatório de Filtragem de Metadados

**Data de Execução:** 13/09/2026 19:20:35

## Resumo

- **Total de tabelas originais:** 295
- **Tabelas mantidas:** 295
- **Tabelas removidas:** 0
- **Percentual removido:** 0.00%

## Critério de Filtragem

Foram removidas **apenas** as tabelas com `row_count = 0` (tabelas vazias).

## Tabelas Removidas

Total de tabelas removidas: **0**

| Schema | Nome da Tabela | Row Count |
|--------|----------------|-----------|

## Tabelas Mantidas

Total de tabelas mantidas: **295**

### Estatísticas das Tabelas Mantidas

- **Menor row_count:** 0
- **Maior row_count:** 1,508
- **Média de row_count:** 49.48

### Amostra das Tabelas Mantidas (primeiras 20)

| Schema | Nome da Tabela | Row Count |
|--------|----------------|-----------|
| magento2 | admin_system_messages | 0 |
| magento2 | admin_user | 0 |
| magento2 | adminnotification_inbox | 0 |
| magento2 | authorization_role | 1 |
| magento2 | authorization_rule | 1 |
| magento2 | captcha_log | 0 |
| magento2 | catalog_category_entity | 27 |
| magento2 | catalog_category_entity_datetime | 6 |
| magento2 | catalog_category_entity_decimal | 4 |
| magento2 | catalog_category_entity_int | 130 |
| magento2 | catalog_category_entity_text | 154 |
| magento2 | catalog_category_entity_varchar | 210 |
| magento2 | catalog_category_product | 132 |
| magento2 | catalog_category_product_index | 1,317 |
| magento2 | catalog_category_product_index_tmp | 0 |
| magento2 | catalog_compare_item | 0 |
| magento2 | catalog_eav_attribute | 118 |
| magento2 | catalog_product_bundle_option | 20 |
| magento2 | catalog_product_bundle_option_value | 20 |
| magento2 | catalog_product_bundle_price_index | 0 |

*... e mais 275 tabelas*

## Justificativa Científica

A remoção de tabelas com `row_count = 0` é justificada pelos seguintes motivos:

1. **Ausência de Dados:** Tabelas vazias não contêm informações que possam contribuir para a análise ou geração de insights pela LLM.

2. **Redução de Ruído:** A inclusão de metadados de tabelas vazias adiciona ruído informacional sem valor semântico ou estatístico.

3. **Otimização de Recursos:** A remoção dessas tabelas reduz o tamanho do payload enviado para a LLM, otimizando o uso de tokens e melhorando a eficiência do processamento.

4. **Foco em Dados Relevantes:** Manter apenas tabelas com dados reais permite que a LLM concentre sua análise em estruturas que efetivamente contêm informação.

---

*Relatório gerado automaticamente pelo script de filtragem de metadados.*
