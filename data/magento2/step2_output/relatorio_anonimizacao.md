# Relatório de Anonimização de Metadados

**Data de Execução:** 13/09/2026 19:20:35

## Resumo

- **Total de tabelas processadas:** 295
- **Tabelas com colunas sensíveis:** 36
- **Total de colunas anonimizadas (contando repetições entre tabelas):** 47
- **Padrões de sensibilidade configurados:** 86
- **Detecção automática de chaves naturais (PK/FK não-numéricas):** ativada
- **Colunas anonimizadas por serem chave natural (não pelo nome):** 19

## Como funciona

As colunas cujo **nome** bateu com algum padrão de sensibilidade foram mantidas
na estrutura do JSON (nome, tipo, nullable), porém todos os seus **valores**
(`stats.sample_values`, `stats.frequent_values` e `sample_rows`) foram
substituídos pelo token `<anonimizado>`.

Além dos padrões de nome, colunas que são **Primary Key ou Foreign Key** e têm
tipo **não-numérico** (varchar/text/char, em vez de int/serial/bigint) também
foram anonimizadas automaticamente — isso cobre o caso de sistemas legados
(comum no e-SUS) onde a própria chave primária/estrangeira é um dado como
CPF ou CNS. Chaves numéricas (ids sequenciais) foram mantidas intactas,
pois normalmente não identificam ninguém sozinhas e são necessárias para o
LLM entender os relacionamentos entre as tabelas.

## Chaves Anonimizadas por Serem Não-Numéricas (revise com atenção)

| Tabela | Coluna |
|--------|--------|
| magento2.admin_system_messages | identity |
| magento2.captcha_log | type |
| magento2.captcha_log | value |
| magento2.catalog_product_index_eav_decimal_idx | value |
| magento2.core_cache | id |
| magento2.core_cache_tag | tag |
| magento2.core_cache_tag | cache_id |
| magento2.core_resource | code |
| magento2.core_session | session_id |
| magento2.customer_form_attribute | form_code |
| magento2.directory_country | country_id |
| magento2.directory_country_region_name | locale |
| magento2.directory_currency_rate | currency_from |
| magento2.directory_currency_rate | currency_to |
| magento2.sales_order_status | status |
| magento2.sales_order_status_label | status |
| magento2.sales_order_status_state | status |
| magento2.sales_order_status_state | state |
| magento2.weee_tax | country |

## Colunas Sensíveis Detectadas (nomes distintos)

| Nome da Coluna | Nº de tabelas em que apareceu |
|----------------|-------------------------------|
| email | 5 |
| email_sent | 4 |
| status | 3 |
| value | 2 |
| template_sender_email | 2 |
| customer_email | 2 |
| identity | 1 |
| password | 1 |
| rp_token | 1 |
| rp_token_created_at | 1 |
| type | 1 |
| id | 1 |
| tag | 1 |
| cache_id | 1 |
| code | 1 |
| session_id | 1 |
| finished_at | 1 |
| form_code | 1 |
| country_id | 1 |
| locale | 1 |
| currency_from | 1 |
| currency_to | 1 |
| login_at | 1 |
| http_accept_charset | 1 |
| http_accept_language | 1 |
| newsletter_sender_email | 1 |
| queue_finish_at | 1 |
| subscriber_email | 1 |
| token | 1 |
| customer_login | 1 |
| cc_cid_status | 1 |
| state | 1 |
| password_hash | 1 |
| cc_cid_enc | 1 |
| country | 1 |

## Detalhe por Tabela

| Tabela | Colunas Anonimizadas (motivo) |
|--------|-------------------------------|
| magento2.admin_system_messages | identity (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.admin_user | email (padrão de nome), password (padrão de nome), rp_token (padrão de nome), rp_token_created_at (padrão de nome) |
| magento2.adminnotification_inbox | - |
| magento2.authorization_role | - |
| magento2.authorization_rule | - |
| magento2.captcha_log | type (PK/FK com tipo não-numérico (possível chave natural)), value (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.catalog_category_entity | - |
| magento2.catalog_category_entity_datetime | - |
| magento2.catalog_category_entity_decimal | - |
| magento2.catalog_category_entity_int | - |
| magento2.catalog_category_entity_text | - |
| magento2.catalog_category_entity_varchar | - |
| magento2.catalog_category_product | - |
| magento2.catalog_category_product_index | - |
| magento2.catalog_category_product_index_tmp | - |
| magento2.catalog_compare_item | - |
| magento2.catalog_eav_attribute | - |
| magento2.catalog_product_bundle_option | - |
| magento2.catalog_product_bundle_option_value | - |
| magento2.catalog_product_bundle_price_index | - |
| magento2.catalog_product_bundle_selection | - |
| magento2.catalog_product_bundle_selection_price | - |
| magento2.catalog_product_bundle_stock_index | - |
| magento2.catalog_product_entity | - |
| magento2.catalog_product_entity_datetime | - |
| magento2.catalog_product_entity_decimal | - |
| magento2.catalog_product_entity_gallery | - |
| magento2.catalog_product_entity_group_price | - |
| magento2.catalog_product_entity_int | - |
| magento2.catalog_product_entity_media_gallery | - |
| magento2.catalog_product_entity_media_gallery_value | - |
| magento2.catalog_product_entity_text | - |
| magento2.catalog_product_entity_tier_price | - |
| magento2.catalog_product_entity_varchar | - |
| magento2.catalog_product_index_eav | - |
| magento2.catalog_product_index_eav_decimal | - |
| magento2.catalog_product_index_eav_decimal_idx | value (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.catalog_product_index_eav_decimal_tmp | - |
| magento2.catalog_product_index_eav_idx | - |
| magento2.catalog_product_index_eav_tmp | - |
| magento2.catalog_product_index_group_price | - |
| magento2.catalog_product_index_price | - |
| magento2.catalog_product_index_price_bundle_idx | - |
| magento2.catalog_product_index_price_bundle_opt_idx | - |
| magento2.catalog_product_index_price_bundle_opt_tmp | - |
| magento2.catalog_product_index_price_bundle_sel_idx | - |
| magento2.catalog_product_index_price_bundle_sel_tmp | - |
| magento2.catalog_product_index_price_bundle_tmp | - |
| magento2.catalog_product_index_price_cfg_opt_agr_idx | - |
| magento2.catalog_product_index_price_cfg_opt_agr_tmp | - |
| magento2.catalog_product_index_price_cfg_opt_idx | - |
| magento2.catalog_product_index_price_cfg_opt_tmp | - |
| magento2.catalog_product_index_price_downlod_idx | - |
| magento2.catalog_product_index_price_downlod_tmp | - |
| magento2.catalog_product_index_price_final_idx | - |
| magento2.catalog_product_index_price_final_tmp | - |
| magento2.catalog_product_index_price_idx | - |
| magento2.catalog_product_index_price_opt_agr_idx | - |
| magento2.catalog_product_index_price_opt_agr_tmp | - |
| magento2.catalog_product_index_price_opt_idx | - |
| magento2.catalog_product_index_price_opt_tmp | - |
| magento2.catalog_product_index_price_tmp | - |
| magento2.catalog_product_index_tier_price | - |
| magento2.catalog_product_index_website | - |
| magento2.catalog_product_link | - |
| magento2.catalog_product_link_attribute | - |
| magento2.catalog_product_link_attribute_decimal | - |
| magento2.catalog_product_link_attribute_int | - |
| magento2.catalog_product_link_attribute_varchar | - |
| magento2.catalog_product_link_type | - |
| magento2.catalog_product_option | - |
| magento2.catalog_product_option_price | - |
| magento2.catalog_product_option_title | - |
| magento2.catalog_product_option_type_price | - |
| magento2.catalog_product_option_type_title | - |
| magento2.catalog_product_option_type_value | - |
| magento2.catalog_product_relation | - |
| magento2.catalog_product_super_attribute | - |
| magento2.catalog_product_super_attribute_label | - |
| magento2.catalog_product_super_attribute_pricing | - |
| magento2.catalog_product_super_link | - |
| magento2.catalog_product_website | - |
| magento2.catalog_url_rewrite_product_category | - |
| magento2.cataloginventory_stock | - |
| magento2.cataloginventory_stock_item | - |
| magento2.cataloginventory_stock_status | - |
| magento2.cataloginventory_stock_status_idx | - |
| magento2.cataloginventory_stock_status_tmp | - |
| magento2.catalogrule | - |
| magento2.catalogrule_affected_product | - |
| magento2.catalogrule_customer_group | - |
| magento2.catalogrule_group_website | - |
| magento2.catalogrule_product | - |
| magento2.catalogrule_product_price | - |
| magento2.catalogrule_website | - |
| magento2.catalogsearch_fulltext | - |
| magento2.checkout_agreement | - |
| magento2.checkout_agreement_store | - |
| magento2.cms_block | - |
| magento2.cms_block_store | - |
| magento2.cms_page | - |
| magento2.cms_page_store | - |
| magento2.core_cache | id (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.core_cache_tag | tag (PK/FK com tipo não-numérico (possível chave natural)), cache_id (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.core_config_data | - |
| magento2.core_flag | - |
| magento2.core_layout_link | - |
| magento2.core_layout_update | - |
| magento2.core_resource | code (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.core_session | session_id (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.core_theme | - |
| magento2.core_theme_file | - |
| magento2.core_variable | - |
| magento2.core_variable_value | - |
| magento2.cron_schedule | finished_at (padrão de nome) |
| magento2.customer_address_entity | - |
| magento2.customer_address_entity_datetime | - |
| magento2.customer_address_entity_decimal | - |
| magento2.customer_address_entity_int | - |
| magento2.customer_address_entity_text | - |
| magento2.customer_address_entity_varchar | - |
| magento2.customer_eav_attribute | - |
| magento2.customer_eav_attribute_website | - |
| magento2.customer_entity | email (padrão de nome) |
| magento2.customer_entity_datetime | - |
| magento2.customer_entity_decimal | - |
| magento2.customer_entity_int | - |
| magento2.customer_entity_text | - |
| magento2.customer_entity_varchar | - |
| magento2.customer_form_attribute | form_code (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.customer_group | - |
| magento2.customer_visitor | - |
| magento2.design_change | - |
| magento2.directory_country | country_id (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.directory_country_format | - |
| magento2.directory_country_region | - |
| magento2.directory_country_region_name | locale (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.directory_currency_rate | currency_from (PK/FK com tipo não-numérico (possível chave natural)), currency_to (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.downloadable_link | - |
| magento2.downloadable_link_price | - |
| magento2.downloadable_link_purchased | - |
| magento2.downloadable_link_purchased_item | - |
| magento2.downloadable_link_title | - |
| magento2.downloadable_sample | - |
| magento2.downloadable_sample_title | - |
| magento2.eav_attribute | - |
| magento2.eav_attribute_group | - |
| magento2.eav_attribute_label | - |
| magento2.eav_attribute_option | - |
| magento2.eav_attribute_option_value | - |
| magento2.eav_attribute_set | - |
| magento2.eav_entity | - |
| magento2.eav_entity_attribute | - |
| magento2.eav_entity_datetime | - |
| magento2.eav_entity_decimal | - |
| magento2.eav_entity_int | - |
| magento2.eav_entity_store | - |
| magento2.eav_entity_text | - |
| magento2.eav_entity_type | - |
| magento2.eav_entity_varchar | - |
| magento2.eav_form_element | - |
| magento2.eav_form_fieldset | - |
| magento2.eav_form_fieldset_label | - |
| magento2.eav_form_type | - |
| magento2.eav_form_type_entity | - |
| magento2.email_template | template_sender_email (padrão de nome) |
| magento2.gift_message | - |
| magento2.googleoptimizer_code | - |
| magento2.googleshopping_attributes | - |
| magento2.googleshopping_items | - |
| magento2.googleshopping_types | - |
| magento2.importexport_importdata | - |
| magento2.indexer_state | - |
| magento2.integration | email (padrão de nome) |
| magento2.log_customer | login_at (padrão de nome) |
| magento2.log_quote | - |
| magento2.log_summary | - |
| magento2.log_summary_type | - |
| magento2.log_url | - |
| magento2.log_url_info | - |
| magento2.log_visitor | - |
| magento2.log_visitor_info | http_accept_charset (padrão de nome), http_accept_language (padrão de nome) |
| magento2.log_visitor_online | - |
| magento2.mview_state | - |
| magento2.newsletter_problem | - |
| magento2.newsletter_queue | newsletter_sender_email (padrão de nome), queue_finish_at (padrão de nome) |
| magento2.newsletter_queue_link | - |
| magento2.newsletter_queue_store_link | - |
| magento2.newsletter_subscriber | subscriber_email (padrão de nome) |
| magento2.newsletter_template | template_sender_email (padrão de nome) |
| magento2.oauth_consumer | - |
| magento2.oauth_nonce | - |
| magento2.oauth_token | token (padrão de nome) |
| magento2.persistent_session | - |
| magento2.product_alert_price | - |
| magento2.product_alert_stock | - |
| magento2.rating | - |
| magento2.rating_entity | - |
| magento2.rating_option | - |
| magento2.rating_option_vote | - |
| magento2.rating_option_vote_aggregated | - |
| magento2.rating_store | - |
| magento2.rating_title | - |
| magento2.report_compared_product_index | - |
| magento2.report_event | - |
| magento2.report_event_types | customer_login (padrão de nome) |
| magento2.report_viewed_product_aggregated_daily | - |
| magento2.report_viewed_product_aggregated_monthly | - |
| magento2.report_viewed_product_aggregated_yearly | - |
| magento2.report_viewed_product_index | - |
| magento2.review | - |
| magento2.review_detail | - |
| magento2.review_entity | - |
| magento2.review_entity_summary | - |
| magento2.review_status | - |
| magento2.review_store | - |
| magento2.sales_bestsellers_aggregated_daily | - |
| magento2.sales_bestsellers_aggregated_monthly | - |
| magento2.sales_bestsellers_aggregated_yearly | - |
| magento2.sales_creditmemo | email_sent (padrão de nome) |
| magento2.sales_creditmemo_comment | - |
| magento2.sales_creditmemo_grid | - |
| magento2.sales_creditmemo_item | - |
| magento2.sales_invoice | email_sent (padrão de nome) |
| magento2.sales_invoice_comment | - |
| magento2.sales_invoice_grid | - |
| magento2.sales_invoice_item | - |
| magento2.sales_invoiced_aggregated | - |
| magento2.sales_invoiced_aggregated_order | - |
| magento2.sales_order | email_sent (padrão de nome), customer_email (padrão de nome) |
| magento2.sales_order_address | email (padrão de nome) |
| magento2.sales_order_aggregated_created | - |
| magento2.sales_order_aggregated_updated | - |
| magento2.sales_order_grid | - |
| magento2.sales_order_item | - |
| magento2.sales_order_payment | cc_cid_status (padrão de nome) |
| magento2.sales_order_status | status (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.sales_order_status_history | - |
| magento2.sales_order_status_label | status (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.sales_order_status_state | status (PK/FK com tipo não-numérico (possível chave natural)), state (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.sales_order_tax | - |
| magento2.sales_order_tax_item | - |
| magento2.sales_payment_transaction | - |
| magento2.sales_quote | customer_email (padrão de nome), password_hash (padrão de nome) |
| magento2.sales_quote_address | email (padrão de nome) |
| magento2.sales_quote_address_item | - |
| magento2.sales_quote_item | - |
| magento2.sales_quote_item_option | - |
| magento2.sales_quote_payment | cc_cid_enc (padrão de nome) |
| magento2.sales_quote_shipping_rate | - |
| magento2.sales_refunded_aggregated | - |
| magento2.sales_refunded_aggregated_order | - |
| magento2.sales_shipment | email_sent (padrão de nome) |
| magento2.sales_shipment_comment | - |
| magento2.sales_shipment_grid | - |
| magento2.sales_shipment_item | - |
| magento2.sales_shipment_track | - |
| magento2.sales_shipping_aggregated | - |
| magento2.sales_shipping_aggregated_order | - |
| magento2.salesrule | - |
| magento2.salesrule_coupon | - |
| magento2.salesrule_coupon_aggregated | - |
| magento2.salesrule_coupon_aggregated_order | - |
| magento2.salesrule_coupon_aggregated_updated | - |
| magento2.salesrule_coupon_usage | - |
| magento2.salesrule_customer | - |
| magento2.salesrule_customer_group | - |
| magento2.salesrule_label | - |
| magento2.salesrule_product_attribute | - |
| magento2.salesrule_website | - |
| magento2.search_query | - |
| magento2.sendfriend_log | - |
| magento2.shipping_tablerate | - |
| magento2.sitemap | - |
| magento2.store | - |
| magento2.store_group | - |
| magento2.store_website | - |
| magento2.tax_calculation | - |
| magento2.tax_calculation_rate | - |
| magento2.tax_calculation_rate_title | - |
| magento2.tax_calculation_rule | - |
| magento2.tax_class | - |
| magento2.tax_order_aggregated_created | - |
| magento2.tax_order_aggregated_updated | - |
| magento2.translation | - |
| magento2.url_rewrite | - |
| magento2.vde_theme_change | - |
| magento2.weee_tax | country (PK/FK com tipo não-numérico (possível chave natural)) |
| magento2.widget | - |
| magento2.widget_instance | - |
| magento2.widget_instance_page | - |
| magento2.widget_instance_page_layout | - |
| magento2.wishlist | - |
| magento2.wishlist_item | - |
| magento2.wishlist_item_option | - |


## PII Encontrada DENTRO de Texto Livre / Colunas Não Marcadas pelo Nome (revise com atenção)

Estas colunas **não** bateram com nenhum padrão de nome sensível, mas continham
CPF, CNS ou e-mail *embutidos* no valor (ex.: um atestado em texto corrido, ou
um JSON serializado como string). Apenas o trecho encontrado foi substituído
por `<pii_removido>` — o resto do texto original foi mantido.

**IMPORTANTE:** esta varredura reconhece apenas padrões numéricos
(CPF/CNS) e e-mail. Ela **não** identifica nomes de pessoas dentro de texto
livre, pois não existe um padrão confiável para isso. Se alguma das colunas
abaixo for um campo narrativo (atestado, laudo, observação clínica etc.),
o ideal é adicionar o nome dela em `sensitive_columns.json` para que a
coluna INTEIRA seja anonimizada, em vez de depender só desta rede de segurança.

Total de colunas com PII de conteúdo detectada: **0**

| Tabela | Colunas com PII embutida |
|--------|---------------------------|
*Nenhuma ocorrência.*


## Justificativa

Dados de saúde (como os do e-SUS) frequentemente contêm identificadores
diretos (CPF, CNS, nome) e quase-identificadores (endereço, data de
nascimento, telefone) que não podem ser enviados a serviços de LLM externos.
Em vez de remover a coluna (o que perde a informação estrutural sobre a
existência do campo, útil para o LLM entender o schema), o valor é
substituído por `<anonimizado>`, preservando a estrutura da tabela sem expor
dado real.

---

*Relatório gerado automaticamente pelo script de anonimização de metadados.*
