# Relatório de Anonimização de Metadados

**Data de Execução:** 13/09/2026 19:19:39

## Resumo

- **Total de tabelas processadas:** 885
- **Tabelas com colunas sensíveis:** 340
- **Total de colunas anonimizadas (contando repetições entre tabelas):** 1447
- **Padrões de sensibilidade configurados:** 86
- **Detecção automática de chaves naturais (PK/FK não-numéricas):** ativada
- **Colunas anonimizadas por serem chave natural (não pelo nome):** 7

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
| public.TB_MIGRACAO_DADOS | installed_rank |
| public.rl_cds_atend_individual_exame | st_solicitado_avaliado |
| public.tb_sessao_sincronizacao | co_unico_sessao |
| public.rl_perfil_cbo_padrao | no_perfil_padrao |
| public.tb_config_sistema | co_config_sistema |
| public.tb_logradouro | co_bairro_dne |
| public.tb_report_etl_configs | co_chave |

## Colunas Sensíveis Detectadas (nomes distintos)

| Nome da Coluna | Nº de tabelas em que apareceu |
|----------------|-------------------------------|
| co_prontuario | 82 |
| nu_cpf_cidadao | 47 |
| co_fat_cidadao_pec | 39 |
| dt_nascimento | 38 |
| nu_cns | 34 |
| co_cid10 | 27 |
| nu_prontuario | 21 |
| no_bairro | 21 |
| ds_complemento | 21 |
| co_cidadao | 18 |
| co_dim_profissional | 17 |
| tp_logradouro | 17 |
| co_dim_profissional_1 | 16 |
| co_dim_profissional_2 | 16 |
| nu_cns_cidadao | 15 |
| co_usuario | 12 |
| ds_email | 12 |
| ds_cep | 12 |
| no_bairro_filtro | 12 |
| no_logradouro | 11 |
| no_cidadao | 10 |
| nu_cep | 10 |
| no_sexo | 10 |
| co_cid10_principal | 9 |
| nu_latitude | 9 |
| nu_longitude | 9 |
| nu_cpf | 9 |
| ds_logradouro | 9 |
| co_raca_cor | 8 |
| st_desconhece_nome_mae | 8 |
| co_etnia | 8 |
| st_desconhece_nome_pai | 8 |
| nu_cpf_responsavel | 8 |
| st_gestante | 8 |
| co_localidade_endereco | 8 |
| co_medicamento | 8 |
| nu_cpf_cns_cidadao | 8 |
| co_unico_ad_cidadao | 7 |
| dt_nascimento_responsavel | 7 |
| nu_fone_referencia | 7 |
| nu_fone_residencia | 7 |
| co_tipo_endereco | 7 |
| no_social_cidadao | 6 |
| nu_telefone_contato | 6 |
| nu_documento_obito | 6 |
| nu_cns_responsavel | 6 |
| nu_cns_cuidador | 6 |
| nu_cpf_cuidador | 6 |
| co_prontuario_grupo | 6 |
| nu_telefone_celular | 5 |
| co_dim_cid | 5 |
| no_cidadao_filtro | 5 |
| no_responsavel_tecnico | 5 |
| nu_cns_responsavel_tecnico | 5 |
| no_logradouro_filtro | 5 |
| nu_nis_pis_pasep | 5 |
| co_aplicacao_medicamento | 5 |
| qt_duracao_tratamento | 5 |
| dt_nascimento_cidadao | 4 |
| no_responsavel | 4 |
| co_cidadao_master | 4 |
| co_responsavel | 4 |
| co_motivo_reserva | 4 |
| st_responsavel_familiar | 4 |
| no_mae_cidadao | 4 |
| ds_email_cidadao | 4 |
| no_pai_cidadao | 4 |
| nu_cpf_cns_responsavel | 4 |
| ds_concentracao | 4 |
| co_unico_alergia | 4 |
| no_modelo | 4 |
| dt_prontuario_lembrete | 4 |
| co_medicamento_catmat | 4 |
| nu_telefone | 4 |
| co_cid10_motivo_indicacao | 4 |
| st_responsavel_vivo | 4 |
| st_responsavel_ainda_reside | 4 |
| co_seq_ad_cidadao | 3 |
| co_cid10_causa_associada | 3 |
| co_cid10_secundario_2 | 3 |
| st_cidadao_sincronizado | 3 |
| co_unico_ad_cidadao_obito | 3 |
| ds_outro_motivo_reserva | 3 |
| st_cidadao_agendamento_online | 3 |
| co_seq_evolucao_aval_ciap_cid | 3 |
| st_responsavel | 3 |
| st_sg_percepcao_saude | 3 |
| no_profissional | 3 |
| co_criticidade_alergia | 3 |
| dt_ultima_alteracao_status | 3 |
| co_seq_atestado | 3 |
| ds_atestado | 3 |
| nu_contato_responsavel_tecnico | 3 |
| co_seq_cidadao | 3 |
| co_unico_cidadao_prontuario | 3 |
| co_unico_prontuario | 3 |
| no_cuidador | 3 |
| dt_nascimento_cuidador | 3 |
| co_unico_cidadao | 3 |
| co_pais_nascimento | 3 |
| st_infrm_orientacao_sexual | 3 |
| tp_orientacao_sexual | 3 |
| st_infrm_identidade_genero | 3 |
| tp_identidade_genero | 3 |
| st_compartilhamento_prontuario | 3 |
| no_mae | 3 |
| no_mae_filtro | 3 |
| no_pai | 3 |
| no_social | 3 |
| nu_telefone_residencial | 3 |
| st_territorio_utiliza_cpf | 3 |
| no_tipo_sanguineo | 3 |
| co_seq_cidadao_grupo | 3 |
| co_cidadao_unificado | 3 |
| co_seq_cidadao_vinculacao_eqp | 3 |
| co_seq_medicamento | 3 |
| co_ultima_receita_medicamento | 3 |
| nu_medicao_saturacao_o2 | 3 |
| no_profissional_filtro | 3 |
| co_seq_prontuario | 3 |
| st_cidadao_processado | 3 |
| co_seq_prontuario_grpo_hstrco | 3 |
| co_seq_receita_medicamento | 3 |
| nu_cnpj | 3 |
| nu_telefone_comercial | 3 |
| nu_telefone_comercial2 | 3 |
| nu_telefone_fax | 3 |
| co_seq_usuario | 3 |
| ds_senha | 3 |
| dt_ultima_atualizacao_senha | 3 |
| st_forcar_troca_senha | 3 |
| st_responsavel_unico | 3 |
| ds_filtro_cids | 3 |
| nu_saturacao_o2 | 3 |
| co_dim_municipio_cidadao | 3 |
| no_nome | 3 |
| ds_ciap_nome_codigo | 3 |
| ds_cid_nome_codigo | 3 |
| no_raca_cor | 2 |
| ds_detalhes | 2 |
| nu_cns_prof | 2 |
| co_equipe_principal | 2 |
| co_agend_principal | 2 |
| nu_telefone1 | 2 |
| nu_telefone2 | 2 |
| ds_email_chefe | 2 |
| co_seq_atend_obs_responsavel | 2 |
| st_atendeu_responsavel | 2 |
| co_lotacao_responsavel | 2 |
| co_seq_cds_cidadao_resposta | 2 |
| nu_pis_pasep | 2 |
| nu_cartao_sus_responsavel | 2 |
| nu_celular_cidadao | 2 |
| nu_declaracao_obito | 2 |
| co_cds_prof_principal | 2 |
| no_identificacao_cidadao | 2 |
| ds_senha_certificado | 2 |
| co_seq_cidadao_nucleo_familiar | 2 |
| nu_cns_profissional | 2 |
| no_etnia | 2 |
| co_dim_identidade_genero | 2 |
| co_alergia_evolucao | 2 |
| co_manifestacao_alergia | 2 |
| co_seq_alergia | 2 |
| co_ultima_alergia_evolucao | 2 |
| co_seq_alergia_evolucao | 2 |
| st_alergia_avaliada | 2 |
| co_tipo_reacao_alergia | 2 |
| co_grau_certeza_alergia | 2 |
| nu_responsavel_anterior | 2 |
| tp_participacao_cidadao | 2 |
| tp_atestado | 2 |
| co_seq_atestado_modelo | 2 |
| ds_modelo | 2 |
| co_cidadao_participante | 2 |
| nu_duracao_atendimento_padrao | 2 |
| st_cidadao_aceita_atend_tic | 2 |
| co_responsavel_cancelamento | 2 |
| no_medicamento_filtro | 2 |
| co_seq_modelo_personalizado | 2 |
| ds_modelo_personalizado | 2 |
| ds_nome | 2 |
| st_possui_cid | 2 |
| no_social_profissional | 2 |
| no_civil_profissional | 2 |
| co_seq_prof_historico_cns | 2 |
| co_seq_substanc_espec_alergia | 2 |
| st_trocar_senha | 2 |
| ds_login | 2 |
| dt_envio_email_recuperar_senha | 2 |
| dt_primeiro_login_versao | 2 |
| no_aplicacao_medicamento | 2 |
| co_cid10_2 | 2 |
| co_cid10_segundo | 2 |
| co_cid10_terceiro | 2 |
| co_localidade_cidadao | 2 |
| co_localidade_cidadao_nasc | 2 |
| nu_fone_responsavel_tecnico | 2 |
| ds_complemento_filtro | 2 |
| co_cds_prof_responsavel | 2 |
| qt_tempo_duracao_consulta | 2 |
| nu_identificador_responsavel | 2 |
| no_responsavel_envio | 2 |
| nu_prontuario_familiar | 2 |
| st_responsavel_cadastrado | 2 |
| st_responsavel_declarado | 2 |
| co_dim_cid10 | 2 |
| co_dim_duracao_tratamento_med | 2 |
| co_dim_via_administracao | 2 |
| co_dim_tp_particip_cidadao | 2 |
| st_tema_saude_cidad_dirt_human | 2 |
| co_dim_raca_cor | 2 |
| co_dim_etnia | 2 |
| co_dim_pais_nascimento | 2 |
| co_dim_tipo_logradouro | 2 |
| no_nome_social | 2 |
| nu_nis | 2 |
| no_nome_mae | 2 |
| no_nome_pai | 2 |
| no_email | 2 |
| nu_telefone_residencia | 2 |
| no_complemento | 2 |
| dt_acesso_prontuario | 2 |
| co_lista_medicamento | 2 |
| installed_rank | 1 |
| co_seq_acomp_cidadaos_vinc | 1 |
| no_sexo_cidadao | 1 |
| tp_identidade_genero_cidadao | 1 |
| dt_ultima_atualizacao_cidadao | 1 |
| nu_fone_residencial | 1 |
| nu_micro_area_tb_cidadao | 1 |
| no_tipo_logradouro_tb_cidadao | 1 |
| ds_logradouro_tb_cidadao | 1 |
| nu_numero_tb_cidadao | 1 |
| st_sem_numero_tb_cidadao | 1 |
| ds_complemento_tb_cidadao | 1 |
| no_bairro_tb_cidadao | 1 |
| no_municipio_tb_cidadao | 1 |
| sg_uf_tb_cidadao | 1 |
| ds_cep_tb_cidadao | 1 |
| no_tipo_logradouro_domicilio | 1 |
| ds_logradouro_domicilio | 1 |
| ds_complemento_domicilio | 1 |
| no_bairro_domicilio | 1 |
| no_municipio_domicilio | 1 |
| ds_cep_domicilio | 1 |
| ds_logradouro_tb_cidadao_filtr | 1 |
| no_bairro_tb_cidadao_filtro | 1 |
| ds_logradouro_domicilio_filtro | 1 |
| no_bairro_domicilio_filtro | 1 |
| co_tipo_endereco_tb_cidadao | 1 |
| no_dsei_tb_cidadao | 1 |
| no_polo_base_tb_cidadao | 1 |
| no_aldeia_tb_cidadao | 1 |
| nu_familia_tb_cidadao | 1 |
| co_tipo_endereco_domicilio | 1 |
| no_dsei_domicilio | 1 |
| no_polo_base_domicilio | 1 |
| no_aldeia_domicilio | 1 |
| co_seq_acomp_cidad_vinc_prcs | 1 |
| co_seq_cat_substancia_alergia | 1 |
| no_categ_substancia_alergia | 1 |
| co_seq_cidadao_bolsa_familia | 1 |
| nu_documento | 1 |
| tp_documento | 1 |
| co_seq_dim_cidadao_pec_grupo | 1 |
| co_seq_dim_via_administracao | 1 |
| no_via_administracao | 1 |
| no_via_administracao_filtro | 1 |
| co_seq_fat_cnsldo_cido_fai_cid | 1 |
| co_seq_fat_conslddo_ciddo_fad | 1 |
| co_seq_fat_conslddo_ciddo_fai | 1 |
| co_dim_tempo_doenca_cardiaca | 1 |
| co_dim_tempo_cnslta_1_prcltra | 1 |
| co_seq_fat_conslddo_ciddo_fao | 1 |
| co_seq_fat_conslddo_ciddo_fci | 1 |
| co_seq_fat_conslddo_ciddo_fp | 1 |
| co_seq_fat_conslddo_ciddo_fvd | 1 |
| no_polo_base | 1 |
| no_polo_base_filtro | 1 |
| no_chefe_polo_base | 1 |
| co_cds_adm_medicamento | 1 |
| no_cds_adm_medicamento | 1 |
| st_solicitado_avaliado | 1 |
| co_unico_sessao | 1 |
| co_cid10_encaminhamento | 1 |
| st_cid_principal | 1 |
| co_seq_dim_cid | 1 |
| nu_cid | 1 |
| no_cid | 1 |
| co_seq_dim_duracao_trat_med | 1 |
| nu_duracao_tratamento_med | 1 |
| no_duracao_tratamento_med | 1 |
| no_duracao_tratamento_med_filt | 1 |
| co_seq_dim_etnia | 1 |
| co_seq_dim_profissional | 1 |
| co_seq_dim_raca_cor | 1 |
| ds_raca_cor | 1 |
| dt_att_cidadao_pec_etl | 1 |
| co_seq_dim_tipo_endereco | 1 |
| ds_tipo_endereco | 1 |
| co_seq_dim_tipo_logradouro | 1 |
| ds_tipo_logradouro | 1 |
| ds_dim_tipo_orientacao_sexual | 1 |
| no_municipio | 1 |
| co_seq_dim_identidade_genero | 1 |
| ds_identidade_genero | 1 |
| co_dim_equipe_principal | 1 |
| co_seq_fat_cidadao_pec | 1 |
| co_dim_tempo_nascimento | 1 |
| co_dim_cid_motivo_indicacao | 1 |
| co_seq_fat_rel_op_gestante | 1 |
| co_seq_grupo_ciap_cid | 1 |
| no_perfil_padrao | 1 |
| ds_email_prof_participante | 1 |
| nu_telefone_prof_participante | 1 |
| co_seq_taalergia | 1 |
| co_seq_taalergiaevolucao | 1 |
| co_seq_taatendobsresponsavel | 1 |
| co_seq_taatestado | 1 |
| im_qrcode_atestado | 1 |
| co_seq_taatestadomodelo | 1 |
| co_seq_compartilha_prontuario | 1 |
| dt_ultima_alteracao | 1 |
| co_seq_tamanifestalergiaevoluc | 1 |
| co_seq_tamedicamento | 1 |
| co_seq_tamedicamentocatmat | 1 |
| co_seq_tamedicamentousocontinu | 1 |
| co_seq_tamodelopersonalizado | 1 |
| co_seq_taprofhistoricocns | 1 |
| co_seq_taprontuario | 1 |
| co_seq_taprontuariogrupohistrc | 1 |
| co_seq_tareceitamedicamento | 1 |
| co_seq_territorio_cidadao_erro | 1 |
| co_seq_tausuario | 1 |
| no_aldeia | 1 |
| no_aldeia_filtro | 1 |
| nu_ano_contato_indigena | 1 |
| dt_inicio_geracao | 1 |
| nu_cid10 | 1 |
| no_cid10 | 1 |
| no_cid10_filtro | 1 |
| nu_cid10_filtro | 1 |
| co_config_sistema | 1 |
| no_criticidade_alergia | 1 |
| co_seq_dim_tipo_cnsulta_odonto | 1 |
| no_dsei | 1 |
| no_dsei_filtro | 1 |
| no_chefe_dsei | 1 |
| co_etnia_cadsus | 1 |
| st_nasf_avaliacao_diagnostico | 1 |
| st_pblc_alvo_gestante | 1 |
| st_pblc_alvo_usuario_tabaco | 1 |
| st_pblc_alvo_usuario_alcool | 1 |
| st_pblc_alvo_usuario_outr_drog | 1 |
| nu_participante_cns | 1 |
| dt_participante_nascimento | 1 |
| nu_cpf_participante | 1 |
| co_dim_cid_principal | 1 |
| co_dim_cid_sec_1 | 1 |
| co_dim_cid_sec_2 | 1 |
| co_dim_uf_cidadao | 1 |
| nu_cep_residencia | 1 |
| no_bairro_residencia | 1 |
| no_logradouro_residencia | 1 |
| nu_num_logradouro_residencia | 1 |
| no_complemento_residencia | 1 |
| co_fat_cidadao_pec_cuidador | 1 |
| nu_num_logradouro | 1 |
| no_instituicao_nome | 1 |
| nu_instituicao_cns | 1 |
| nu_instituicao_telefone | 1 |
| co_dim_tipo_endereco | 1 |
| st_doenca_respiratoria | 1 |
| st_doenca_respira_asma | 1 |
| st_doenca_respira_dpoc_enfisem | 1 |
| st_doenca_respira_outra | 1 |
| st_doenca_respira_n_sabe | 1 |
| st_doenca_cardiaca | 1 |
| st_doenca_card_insuficiencia | 1 |
| st_doenca_card_outro | 1 |
| st_doenca_card_n_sabe | 1 |
| co_dim_tipo_orientacao_sexual | 1 |
| co_dim_cbo_cidadao | 1 |
| st_informar_orientacao_sexual | 1 |
| st_informar_identidade_genero | 1 |
| st_processo_cidadao | 1 |
| nu_celular | 1 |
| co_fat_cidadao_pec_responsvl | 1 |
| co_seq_fat_cidadao | 1 |
| co_fat_cidadao_raiz | 1 |
| co_fat_cidadao_pai1 | 1 |
| co_fat_cidadao_pai2 | 1 |
| co_fat_cidadao_raiz_equipe | 1 |
| co_fat_cidadao_pai1_equipe | 1 |
| co_fat_cidadao_pai2_equipe | 1 |
| co_fat_cidadao_raiz_undde_sade | 1 |
| co_fat_cidadao_pai1_undde_sade | 1 |
| co_fat_cidadao_pai2_undde_sade | 1 |
| co_fat_cidadao_raiz_municipio | 1 |
| co_fat_cidadao_pai1_municipio | 1 |
| co_fat_cidadao_pai2_municipio | 1 |
| co_seq_fat_cidadao_territorio | 1 |
| st_responsavel_informado | 1 |
| st_responsavel_com_fci | 1 |
| st_cns_null | 1 |
| st_cidadao_consistente | 1 |
| co_fat_ciddo_terrtrio_resp | 1 |
| st_processado_cidadao_respnsvl | 1 |
| co_dim_profissional_evolucao | 1 |
| co_dim_sexo_cidadao | 1 |
| co_dim_profissional_solicitant | 1 |
| co_dim_profissional_executante | 1 |
| co_fat_cidadao | 1 |
| st_responsavel_declarado_ci | 1 |
| st_processo_att_cidadao | 1 |
| co_fat_cidadao_territorio | 1 |
| st_acomp_gestante | 1 |
| st_acomp_pessoa_doenca_cronica | 1 |
| st_acomp_usuario_alcool | 1 |
| st_acomp_usuario_outras_drogra | 1 |
| co_seq_grau_certeza_alergia | 1 |
| no_grau_certeza_alergia | 1 |
| co_seq_grupo_condicao_saude | 1 |
| nu_cpf_estagiario | 1 |
| ds_cid10_principal | 1 |
| ds_cid10_secundario_um | 1 |
| ds_cid10_secundario_dois | 1 |
| no_nome_finalizador_obs | 1 |
| nu_cns_finalizador_obs | 1 |
| ds_ciap_nome | 1 |
| ds_cid_nome | 1 |
| ds_cid_codigo | 1 |
| nu_cns_solicitante | 1 |
| no_nome_solicitante | 1 |
| nu_cns_executante | 1 |
| no_nome_executante | 1 |
| ds_proced_nome_codigo | 1 |
| st_atestado | 1 |
| st_medicamento | 1 |
| st_alergia | 1 |
| st_resultado_exame | 1 |
| ds_vacina_nome_sigla | 1 |
| co_cidadao_grupo | 1 |
| tp_lista_medicamento | 1 |
| ds_lista_medicamento | 1 |
| co_logradouro | 1 |
| no_logradouro_exibicao | 1 |
| ds_letra_numero_complemento | 1 |
| co_bairro_dne | 1 |
| co_seq_manifestacao_alergia | 1 |
| no_manifestacao_alergia | 1 |
| no_filtro_manifestacao_alergia | 1 |
| co_migracao_estrutura | 1 |
| no_autor_migracao | 1 |
| no_arquivo_migracao | 1 |
| no_motivo_reserva | 1 |
| co_parte_bucal_cid10 | 1 |
| co_seq_processamento_dom_cid | 1 |
| co_raca_cor_cadsus | 1 |
| no_responsavel_envio_filtro | 1 |
| co_token | 1 |
| no_principal | 1 |
| dt_expiracao | 1 |
| co_chave | 1 |
| co_seq_substancia_alergia | 1 |
| co_cat_substancia_alergia | 1 |
| no_substancia_alergia | 1 |
| no_filtro_substancia_alergia | 1 |
| no_tipo_endereco | 1 |
| co_tipo_logradouro | 1 |
| no_tipo_logradouro | 1 |
| no_tipo_logradouro_filtro | 1 |
| co_tp_logradouro_cadsus | 1 |
| co_seq_tipo_reacao_alergia | 1 |
| no_tipo_reacao_alergia | 1 |
| co_seq_ad_cidadao_historico | 1 |
| ds_alergia_medicamento | 1 |
| dt_atestado | 1 |
| st_nao_possui_cns | 1 |
| dt_ultima_alteracao_cns | 1 |
| co_seq_cns | 1 |
| tempo_duracao_consulta | 1 |

## Detalhe por Tabela

| Tabela | Colunas Anonimizadas (motivo) |
|--------|-------------------------------|
| public.TB_MIGRACAO_DADOS | installed_rank (PK/FK com tipo não-numérico (possível chave natural)) |
| public.rl_aldeia_localidade | - |
| public.rl_antecedente_ciap | co_prontuario (padrão de nome) |
| public.rl_arquivo_atendprof | - |
| public.rl_atend_obs_responsavel | co_seq_atend_obs_responsavel (padrão de nome), co_responsavel (padrão de nome), st_atendeu_responsavel (padrão de nome) |
| public.rl_atend_proced | co_cid10_principal (padrão de nome) |
| public.rl_atend_prof_conduta | - |
| public.rl_atend_prof_odonto_tipo_encm | - |
| public.rl_atend_prof_odonto_tipo_frnc | - |
| public.rl_atend_tipo_servico | - |
| public.rl_ativ_col_lot_env | - |
| public.rl_ativ_col_pratica_saude | - |
| public.rl_ativ_col_publico_alvo | - |
| public.rl_ativ_col_tema_reuniao | - |
| public.rl_ativ_col_tema_saude | - |
| public.rl_ator_papel_perfil | - |
| public.rl_calendario_vacnl_grupo_alvo | - |
| public.rl_cds_atend_dom_proced | - |
| public.rl_cds_atend_dom_situacao_pres | - |
| public.rl_cds_atend_individual_ciap | - |
| public.rl_cds_atend_individual_condut | - |
| public.rl_cds_atend_individual_exame | st_solicitado_avaliado (PK/FK com tipo não-numérico (possível chave natural)) |
| public.rl_cds_atend_individual_nasf | - |
| public.rl_cds_atend_odont_tip_vig_buc | - |
| public.rl_cds_atend_odonto_proced | - |
| public.rl_cds_atend_odonto_tipo_cnslt | - |
| public.rl_cds_atend_odonto_tipo_encam | - |
| public.rl_cds_atend_odonto_tipo_fornc | - |
| public.rl_cds_aval_eleg_ad_tipo_inelg | - |
| public.rl_cds_aval_eleg_cds_situc_prs | - |
| public.rl_cds_ficha_atend_indivdl_prf | - |
| public.rl_cds_ficha_atend_odonto_prof | - |
| public.rl_cds_ficha_ativ_col_pratica | - |
| public.rl_cds_ficha_ativ_col_prof | - |
| public.rl_cds_ficha_ativ_col_pub_alvo | - |
| public.rl_cds_ficha_ativ_col_tema | - |
| public.rl_cds_visita_dom_motivo | - |
| public.rl_ciap_cid10 | co_cid10 (padrão de nome) |
| public.rl_evol_aval_tp_vig_saude_bucl | - |
| public.rl_evolucao_avaliacao_ciap_cid | co_seq_evolucao_aval_ciap_cid (padrão de nome), co_cid10 (padrão de nome) |
| public.rl_evolucao_odonto_parte_bucal | - |
| public.rl_evolucao_odonto_proced | - |
| public.rl_evolucao_plano_ciap | - |
| public.rl_evolucao_subjetivo_ciap | - |
| public.rl_grupo_condicao_ciap_cid | co_seq_grupo_ciap_cid (padrão de nome), co_cid10 (padrão de nome) |
| public.rl_historico_cabecalho | - |
| public.rl_inscrito_topico_notificacao | - |
| public.rl_manifest_alergiaevolucao | co_alergia_evolucao (padrão de nome), co_manifestacao_alergia (padrão de nome) |
| public.rl_perfil_cbo_padrao | no_perfil_padrao (PK/FK com tipo não-numérico (possível chave natural)) |
| public.rl_proced_atributo_complem | - |
| public.rl_proced_cbo | - |
| public.rl_proced_cds_proced | - |
| public.rl_proced_cid10 | co_cid10 (padrão de nome), st_cid_principal (padrão de nome) |
| public.rl_proced_exame_detalhe | - |
| public.rl_proced_grupo_exame | - |
| public.rl_proced_tipo_registro | - |
| public.rl_prof_municipio | - |
| public.rl_qst_associacao_opcao_pergnt | - |
| public.rl_qst_resposta_opcao_pergunta | - |
| public.rl_recurso_acao | - |
| public.rl_respostamca_opcaomca | - |
| public.rl_situacaoface_evolucaodente | - |
| public.rl_situacaoraiz_evolucaodente | - |
| public.rl_tecido_mole_lesao | - |
| public.rl_tipo_atend_proced_automatic | - |
| public.rl_tipo_consulta_odnt_prc_auto | - |
| public.rl_tipo_encam_odonto_procd_aut | - |
| public.rl_tipo_servico_padrao | - |
| public.rl_unidade_medida_dose | - |
| public.rl_unidade_saude_complexidade | - |
| public.rl_unidade_saude_tipo_servico | - |
| public.rl_via_adm_local_apl_vacina | - |
| public.ta_ad_cidadao | co_seq_ad_cidadao (padrão de nome), co_cid10_principal (padrão de nome), co_cid10_causa_associada (padrão de nome), co_prontuario (padrão de nome), co_cid10_secundario_2 (padrão de nome), st_cidadao_sincronizado (padrão de nome), nu_documento_obito (padrão de nome), co_unico_ad_cidadao_obito (padrão de nome), co_unico_ad_cidadao (padrão de nome) |
| public.ta_adm_geral | - |
| public.ta_adm_municipal | - |
| public.ta_agend_compartilhado | co_agend_principal (padrão de nome), ds_email_prof_participante (padrão de nome), nu_telefone_prof_participante (padrão de nome) |
| public.ta_agendado | co_motivo_reserva (padrão de nome), ds_outro_motivo_reserva (padrão de nome), co_prontuario (padrão de nome), st_cidadao_agendamento_online (padrão de nome) |
| public.ta_alergia | co_seq_taalergia (padrão de nome), co_seq_alergia (padrão de nome), co_ultima_alergia_evolucao (padrão de nome), co_prontuario (padrão de nome), co_unico_alergia (padrão de nome) |
| public.ta_alergia_evolucao | co_seq_taalergiaevolucao (padrão de nome), co_seq_alergia_evolucao (padrão de nome), co_unico_alergia (padrão de nome), st_alergia_avaliada (padrão de nome), co_criticidade_alergia (padrão de nome), co_tipo_reacao_alergia (padrão de nome), co_grau_certeza_alergia (padrão de nome) |
| public.ta_animais_domicilio | - |
| public.ta_antecedente | co_prontuario (padrão de nome) |
| public.ta_antecedente_ciap | co_prontuario (padrão de nome) |
| public.ta_antecedente_historico | - |
| public.ta_antecedente_item | - |
| public.ta_arquivo | - |
| public.ta_arquivo_atendprof | - |
| public.ta_atend | co_responsavel (padrão de nome), co_prontuario (padrão de nome), nu_responsavel_anterior (padrão de nome), dt_ultima_alteracao_status (padrão de nome) |
| public.ta_atend_obs | - |
| public.ta_atend_obs_plano_cuidado | - |
| public.ta_atend_obs_responsavel | co_seq_taatendobsresponsavel (padrão de nome), co_seq_atend_obs_responsavel (padrão de nome), co_responsavel (padrão de nome), st_atendeu_responsavel (padrão de nome) |
| public.ta_atend_proced | co_cid10_principal (padrão de nome) |
| public.ta_atend_prof | co_unico_ad_cidadao (padrão de nome), tp_participacao_cidadao (padrão de nome) |
| public.ta_atend_prof_conduta | - |
| public.ta_atend_prof_obs | - |
| public.ta_atend_prof_odonto | - |
| public.ta_atend_prof_odonto_tipo_encm | - |
| public.ta_atend_prof_odonto_tipo_frnc | - |
| public.ta_atend_prof_pre_natal | - |
| public.ta_atend_prof_puericultura | - |
| public.ta_atend_tipo_servico | - |
| public.ta_atestado | co_seq_taatestado (padrão de nome), co_seq_atestado (padrão de nome), ds_atestado (padrão de nome), co_prontuario (padrão de nome), im_qrcode_atestado (padrão de nome), tp_atestado (padrão de nome), co_cid10 (padrão de nome) |
| public.ta_atestado_modelo | co_seq_taatestadomodelo (padrão de nome), co_seq_atestado_modelo (padrão de nome), no_modelo (padrão de nome), ds_modelo (padrão de nome) |
| public.ta_ativ_col_lot_env | - |
| public.ta_ativ_col_pratica_saude | - |
| public.ta_ativ_col_publico_alvo | - |
| public.ta_ativ_col_registro_particip | co_cidadao (padrão de nome), co_cidadao_participante (padrão de nome) |
| public.ta_ativ_col_tema_reuniao | - |
| public.ta_ativ_col_tema_saude | - |
| public.ta_ativacao_agendamento_online | - |
| public.ta_atividade_coletiva | co_lotacao_responsavel (padrão de nome) |
| public.ta_ator_papel | - |
| public.ta_ator_papel_perfil | - |
| public.ta_cbo_atend | - |
| public.ta_cds_domicilio | tp_logradouro (padrão de nome), ds_complemento (padrão de nome), no_logradouro (padrão de nome), no_bairro (padrão de nome), ds_cep (padrão de nome), nu_fone_referencia (padrão de nome), nu_fone_residencia (padrão de nome), no_responsavel_tecnico (padrão de nome), nu_cns_responsavel_tecnico (padrão de nome), nu_contato_responsavel_tecnico (padrão de nome), nu_latitude (padrão de nome), nu_longitude (padrão de nome), no_bairro_filtro (padrão de nome), no_logradouro_filtro (padrão de nome), nu_cns (padrão de nome), co_tipo_endereco (padrão de nome) |
| public.ta_cfg_agenda | - |
| public.ta_cfg_agenda_detalhe | - |
| public.ta_cfg_agenda_municipal | nu_duracao_atendimento_padrao (padrão de nome) |
| public.ta_cfg_agenda_online_detalhe | - |
| public.ta_cfg_certificado | ds_senha_certificado (padrão de nome) |
| public.ta_cidadao | co_seq_cidadao (padrão de nome), co_unico_cidadao_prontuario (padrão de nome), co_unico_prontuario (padrão de nome), st_desconhece_nome_mae (padrão de nome), nu_nis_pis_pasep (padrão de nome), nu_cns_responsavel (padrão de nome), no_responsavel (padrão de nome), dt_nascimento_responsavel (padrão de nome), nu_cns_cuidador (padrão de nome), no_cuidador (padrão de nome), dt_nascimento_cuidador (padrão de nome), co_unico_cidadao (padrão de nome), co_pais_nascimento (padrão de nome), st_desconhece_nome_pai (padrão de nome), st_infrm_orientacao_sexual (padrão de nome), tp_orientacao_sexual (padrão de nome), st_infrm_identidade_genero (padrão de nome), tp_identidade_genero (padrão de nome), st_compartilhamento_prontuario (padrão de nome), nu_cpf (padrão de nome), nu_cns (padrão de nome), no_cidadao (padrão de nome), no_cidadao_filtro (padrão de nome), co_raca_cor (padrão de nome), co_etnia (padrão de nome), dt_nascimento (padrão de nome), no_mae (padrão de nome), no_mae_filtro (padrão de nome), no_pai (padrão de nome), no_social (padrão de nome), nu_documento_obito (padrão de nome), ds_cep (padrão de nome), ds_complemento (padrão de nome), ds_logradouro (padrão de nome), co_localidade_endereco (padrão de nome), no_bairro (padrão de nome), no_bairro_filtro (padrão de nome), tp_logradouro (padrão de nome), nu_telefone_residencial (padrão de nome), nu_telefone_celular (padrão de nome), nu_telefone_contato (padrão de nome), ds_email (padrão de nome), st_territorio_utiliza_cpf (padrão de nome), nu_cpf_cuidador (padrão de nome), nu_cpf_responsavel (padrão de nome), no_tipo_sanguineo (padrão de nome), no_sexo (padrão de nome), co_tipo_endereco (padrão de nome) |
| public.ta_cidadao_grupo | co_seq_cidadao_grupo (padrão de nome), nu_cns (padrão de nome), co_cidadao (padrão de nome), co_cidadao_master (padrão de nome), co_cidadao_unificado (padrão de nome), nu_cpf (padrão de nome) |
| public.ta_cidadao_vinculacao_equipe | co_seq_cidadao_vinculacao_eqp (padrão de nome), co_cidadao (padrão de nome) |
| public.ta_compartilhamento_prontuario | co_seq_compartilha_prontuario (padrão de nome), co_usuario (padrão de nome), dt_ultima_alteracao (padrão de nome) |
| public.ta_config_agenda_fechamento | - |
| public.ta_config_sistema | - |
| public.ta_cuidado_compartilhado | co_prontuario (padrão de nome), co_cid10 (padrão de nome), st_cidadao_aceita_atend_tic (padrão de nome) |
| public.ta_cuidado_compartilhado_evol | - |
| public.ta_encaminhamento | co_prontuario (padrão de nome), ds_complemento (padrão de nome), co_cid10 (padrão de nome) |
| public.ta_equipe | - |
| public.ta_evol_aval_tp_vig_saude_bucl | - |
| public.ta_evolucao_avaliacao | - |
| public.ta_evolucao_avaliacao_ciap_cid | co_seq_evolucao_aval_ciap_cid (padrão de nome), co_cid10 (padrão de nome) |
| public.ta_evolucao_dente | - |
| public.ta_evolucao_objetivo | - |
| public.ta_evolucao_odonto | co_prontuario (padrão de nome) |
| public.ta_evolucao_odonto_parte_bucal | - |
| public.ta_evolucao_odonto_proced | - |
| public.ta_evolucao_plano | - |
| public.ta_evolucao_plano_ciap | - |
| public.ta_evolucao_subjetivo | - |
| public.ta_evolucao_subjetivo_ciap | - |
| public.ta_exame_clearance_creatina | - |
| public.ta_exame_colesterol_hdl | - |
| public.ta_exame_colesterol_ldl | - |
| public.ta_exame_colesterol_total | - |
| public.ta_exame_creatina_serica | - |
| public.ta_exame_hemoglobina_glicada | - |
| public.ta_exame_prenatal | - |
| public.ta_exame_puericultura | - |
| public.ta_exame_requisitado | co_prontuario (padrão de nome) |
| public.ta_exame_triglicerideos | - |
| public.ta_gestor_municipal | - |
| public.ta_imunobiologico_lote | - |
| public.ta_ivcf | co_prontuario (padrão de nome), st_sg_percepcao_saude (padrão de nome) |
| public.ta_ivcf_aplicacao | - |
| public.ta_justificativa_agenda | co_responsavel_cancelamento (padrão de nome), co_usuario (padrão de nome) |
| public.ta_lembrete | co_prontuario (padrão de nome) |
| public.ta_lembrete_evolucao | dt_prontuario_lembrete (padrão de nome) |
| public.ta_lotacao | - |
| public.ta_manifest_alergiaevolucao | co_seq_tamanifestalergiaevoluc (padrão de nome), co_alergia_evolucao (padrão de nome), co_manifestacao_alergia (padrão de nome) |
| public.ta_marcador_consumo_alimentar | - |
| public.ta_medicamento | co_seq_tamedicamento (padrão de nome), co_seq_medicamento (padrão de nome), ds_concentracao (padrão de nome) |
| public.ta_medicamento_catmat | co_seq_tamedicamentocatmat (padrão de nome), co_medicamento_catmat (padrão de nome), co_medicamento (padrão de nome), no_medicamento_filtro (padrão de nome) |
| public.ta_medicamento_uso_continuo | co_seq_tamedicamentousocontinu (padrão de nome), co_medicamento (padrão de nome), co_prontuario (padrão de nome), co_ultima_receita_medicamento (padrão de nome) |
| public.ta_medicao | nu_medicao_saturacao_o2 (padrão de nome) |
| public.ta_modelo_personalizado | co_seq_tamodelopersonalizado (padrão de nome), co_seq_modelo_personalizado (padrão de nome), no_modelo (padrão de nome), ds_modelo_personalizado (padrão de nome) |
| public.ta_neuro_alter_fenot | co_prontuario (padrão de nome) |
| public.ta_neuro_alter_fenot_evolucao | - |
| public.ta_neuro_fator_risco | co_prontuario (padrão de nome) |
| public.ta_neuro_fator_risco_evolucao | - |
| public.ta_neuro_marco | co_prontuario (padrão de nome) |
| public.ta_neuro_marco_evolucao | - |
| public.ta_nodo | ds_nome (padrão de nome) |
| public.ta_odontograma | co_prontuario (padrão de nome) |
| public.ta_orientacao | co_prontuario (padrão de nome) |
| public.ta_perfil | - |
| public.ta_perfil_recurso | - |
| public.ta_periograma_simplificado | co_prontuario (padrão de nome) |
| public.ta_pre_natal | co_prontuario (padrão de nome) |
| public.ta_problema | co_cid10 (padrão de nome), co_prontuario (padrão de nome) |
| public.ta_problema_evolucao | st_possui_cid (padrão de nome) |
| public.ta_prof | nu_cpf (padrão de nome), nu_cns (padrão de nome), no_profissional (padrão de nome), no_profissional_filtro (padrão de nome), dt_nascimento (padrão de nome), nu_telefone (padrão de nome), ds_email (padrão de nome), ds_cep (padrão de nome), ds_complemento (padrão de nome), ds_logradouro (padrão de nome), co_localidade_endereco (padrão de nome), no_bairro (padrão de nome), no_bairro_filtro (padrão de nome), tp_logradouro (padrão de nome), co_usuario (padrão de nome), no_sexo (padrão de nome), no_social_profissional (padrão de nome), no_civil_profissional (padrão de nome) |
| public.ta_prof_historico_cns | co_seq_taprofhistoricocns (padrão de nome), co_seq_prof_historico_cns (padrão de nome), nu_cns (padrão de nome) |
| public.ta_prontuario | co_seq_taprontuario (padrão de nome), co_seq_prontuario (padrão de nome), co_prontuario_grupo (padrão de nome), co_cidadao (padrão de nome), st_cidadao_processado (padrão de nome) |
| public.ta_prontuario_grupo_historico | co_seq_taprontuariogrupohistrc (padrão de nome), co_seq_prontuario_grpo_hstrco (padrão de nome), co_prontuario_grupo (padrão de nome), co_prontuario (padrão de nome) |
| public.ta_receita_medicamento | co_seq_tareceitamedicamento (padrão de nome), co_seq_receita_medicamento (padrão de nome), co_aplicacao_medicamento (padrão de nome), co_medicamento (padrão de nome), qt_duracao_tratamento (padrão de nome) |
| public.ta_registro_vacinacao | co_cid10_motivo_indicacao (padrão de nome) |
| public.ta_requisicao_exame | co_cid10 (padrão de nome) |
| public.ta_resposta_mca | - |
| public.ta_respostamca_opcaomca | - |
| public.ta_retificacao_atend | co_prontuario (padrão de nome) |
| public.ta_sinan_notificacao_evolucao | co_prontuario (padrão de nome) |
| public.ta_situacaoface_evolucaodente | - |
| public.ta_situacaoraiz_evolucaodente | - |
| public.ta_substancia_espec_alergia | co_seq_substanc_espec_alergia (padrão de nome), co_medicamento_catmat (padrão de nome) |
| public.ta_tecido_mole | co_prontuario (padrão de nome), co_cid10 (padrão de nome) |
| public.ta_tecido_mole_lesao | - |
| public.ta_territorio_cidadao_erro | co_seq_territorio_cidadao_erro (padrão de nome), co_cidadao (padrão de nome) |
| public.ta_tipo_servico | - |
| public.ta_unidade_saude | nu_cnpj (padrão de nome), nu_telefone_comercial (padrão de nome), nu_telefone_comercial2 (padrão de nome), nu_telefone_fax (padrão de nome), ds_email (padrão de nome), ds_cep (padrão de nome), ds_complemento (padrão de nome), ds_logradouro (padrão de nome), co_localidade_endereco (padrão de nome), no_bairro (padrão de nome), no_bairro_filtro (padrão de nome), tp_logradouro (padrão de nome) |
| public.ta_unidade_saude_complexidade | - |
| public.ta_unidade_saude_tipo_servico | - |
| public.ta_usuario | co_seq_tausuario (padrão de nome), co_seq_usuario (padrão de nome), ds_senha (padrão de nome), st_trocar_senha (padrão de nome), dt_ultima_atualizacao_senha (padrão de nome), st_forcar_troca_senha (padrão de nome), ds_login (padrão de nome), dt_envio_email_recuperar_senha (padrão de nome), dt_primeiro_login_versao (padrão de nome) |
| public.ta_vacinacao | st_gestante (padrão de nome), co_prontuario (padrão de nome) |
| public.ta_videochamada | - |
| public.ta_vinculacao_equipes | co_equipe_principal (padrão de nome) |
| public.tb_acomp_cidadaos_vinc_prcs | co_seq_acomp_cidad_vinc_prcs (padrão de nome) |
| public.tb_acomp_cidadaos_vinculados | co_seq_acomp_cidadaos_vinc (padrão de nome), no_cidadao (padrão de nome), no_social_cidadao (padrão de nome), dt_nascimento_cidadao (padrão de nome), no_sexo_cidadao (padrão de nome), tp_identidade_genero_cidadao (padrão de nome), nu_cpf_cidadao (padrão de nome), nu_cns_cidadao (padrão de nome), nu_telefone_celular (padrão de nome), nu_telefone_contato (padrão de nome), dt_ultima_atualizacao_cidadao (padrão de nome), co_cidadao (padrão de nome), no_responsavel (padrão de nome), nu_fone_residencial (padrão de nome), nu_micro_area_tb_cidadao (padrão de nome), no_tipo_logradouro_tb_cidadao (padrão de nome), ds_logradouro_tb_cidadao (padrão de nome), nu_numero_tb_cidadao (padrão de nome), st_sem_numero_tb_cidadao (padrão de nome), ds_complemento_tb_cidadao (padrão de nome), no_bairro_tb_cidadao (padrão de nome), no_municipio_tb_cidadao (padrão de nome), sg_uf_tb_cidadao (padrão de nome), ds_cep_tb_cidadao (padrão de nome), no_tipo_logradouro_domicilio (padrão de nome), ds_logradouro_domicilio (padrão de nome), ds_complemento_domicilio (padrão de nome), no_bairro_domicilio (padrão de nome), no_municipio_domicilio (padrão de nome), ds_cep_domicilio (padrão de nome), ds_logradouro_tb_cidadao_filtr (padrão de nome), no_bairro_tb_cidadao_filtro (padrão de nome), ds_logradouro_domicilio_filtro (padrão de nome), no_bairro_domicilio_filtro (padrão de nome), no_raca_cor (padrão de nome), co_tipo_endereco_tb_cidadao (padrão de nome), no_dsei_tb_cidadao (padrão de nome), no_polo_base_tb_cidadao (padrão de nome), no_aldeia_tb_cidadao (padrão de nome), nu_familia_tb_cidadao (padrão de nome), co_tipo_endereco_domicilio (padrão de nome), no_dsei_domicilio (padrão de nome), no_polo_base_domicilio (padrão de nome), no_aldeia_domicilio (padrão de nome), co_fat_cidadao_pec (padrão de nome) |
| public.tb_ad_cidadao | co_seq_ad_cidadao (padrão de nome), co_cid10_principal (padrão de nome), co_cid10_causa_associada (padrão de nome), co_prontuario (padrão de nome), co_cid10_secundario_2 (padrão de nome), st_cidadao_sincronizado (padrão de nome), nu_documento_obito (padrão de nome), co_unico_ad_cidadao_obito (padrão de nome), co_unico_ad_cidadao (padrão de nome) |
| public.tb_ad_destino | - |
| public.tb_ad_modalidade | - |
| public.tb_ad_origem | - |
| public.tb_ad_tipo_elegivel | - |
| public.tb_ad_tipo_inelegivel | - |
| public.tb_adm_geral | - |
| public.tb_adm_municipal | - |
| public.tb_agend_compartilhado | co_agend_principal (padrão de nome) |
| public.tb_agenda_fixada_ator_papel | - |
| public.tb_agendado | co_motivo_reserva (padrão de nome), ds_outro_motivo_reserva (padrão de nome), co_prontuario (padrão de nome), st_cidadao_agendamento_online (padrão de nome) |
| public.tb_aldeia | no_aldeia (padrão de nome), no_aldeia_filtro (padrão de nome), nu_cep (padrão de nome), nu_ano_contato_indigena (padrão de nome) |
| public.tb_alergia | co_seq_alergia (padrão de nome), co_ultima_alergia_evolucao (padrão de nome), co_prontuario (padrão de nome), co_unico_alergia (padrão de nome) |
| public.tb_alergia_evolucao | co_seq_alergia_evolucao (padrão de nome), co_unico_alergia (padrão de nome), st_alergia_avaliada (padrão de nome), co_criticidade_alergia (padrão de nome), co_tipo_reacao_alergia (padrão de nome), co_grau_certeza_alergia (padrão de nome) |
| public.tb_alim_bebida | - |
| public.tb_animais_domicilio | - |
| public.tb_antecedente | co_prontuario (padrão de nome) |
| public.tb_antecedente_historico | - |
| public.tb_antecedente_item | - |
| public.tb_antecedente_tipo_item | - |
| public.tb_aplicacao_medicamento | co_aplicacao_medicamento (padrão de nome), no_aplicacao_medicamento (padrão de nome) |
| public.tb_arcada | - |
| public.tb_arquivo | - |
| public.tb_arquivo_temporario | dt_inicio_geracao (padrão de nome), co_usuario (padrão de nome) |
| public.tb_atend | co_responsavel (padrão de nome), co_prontuario (padrão de nome), nu_responsavel_anterior (padrão de nome), dt_ultima_alteracao_status (padrão de nome) |
| public.tb_atend_obs | - |
| public.tb_atend_obs_plano_cuidado | - |
| public.tb_atend_prof | co_unico_ad_cidadao (padrão de nome), tp_participacao_cidadao (padrão de nome) |
| public.tb_atend_prof_obs | - |
| public.tb_atend_prof_odonto | - |
| public.tb_atend_prof_pre_natal | - |
| public.tb_atend_prof_puericultura | - |
| public.tb_atend_prof_tipo_encam_intrn | - |
| public.tb_atestado | co_seq_atestado (padrão de nome), ds_atestado (padrão de nome), co_prontuario (padrão de nome), tp_atestado (padrão de nome), co_cid10 (padrão de nome) |
| public.tb_atestado_modelo | co_seq_atestado_modelo (padrão de nome), no_modelo (padrão de nome), ds_modelo (padrão de nome) |
| public.tb_ativ_col_registro_particip | co_cidadao (padrão de nome), co_cidadao_participante (padrão de nome) |
| public.tb_ativacao_agendamento_online | - |
| public.tb_atividade_coletiva | co_lotacao_responsavel (padrão de nome) |
| public.tb_ator | - |
| public.tb_ator_papel | - |
| public.tb_atributo_complem | - |
| public.tb_auditoria_evento | co_usuario (padrão de nome), ds_detalhes (padrão de nome) |
| public.tb_bairro | no_bairro (padrão de nome), no_bairro_filtro (padrão de nome) |
| public.tb_beneficio | - |
| public.tb_calendario_vacinal | - |
| public.tb_categ_substancia_alergia | co_seq_cat_substancia_alergia (padrão de nome), no_categ_substancia_alergia (padrão de nome) |
| public.tb_categoria_agente_causador | - |
| public.tb_categoria_arquivo_atendprof | - |
| public.tb_cbo | - |
| public.tb_cbo_atend | - |
| public.tb_cds_adm_medicamento | co_cds_adm_medicamento (padrão de nome), no_cds_adm_medicamento (padrão de nome) |
| public.tb_cds_aleitamento_materno | - |
| public.tb_cds_atend_domiciliar | dt_nascimento (padrão de nome), co_cid10 (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_cds_atend_individual | co_prontuario (padrão de nome), nu_prontuario (padrão de nome), dt_nascimento (padrão de nome), co_cid10 (padrão de nome), co_cid10_2 (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_cds_atend_odonto | nu_prontuario (padrão de nome), dt_nascimento (padrão de nome), st_gestante (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_cds_ativ_col_participante | dt_nascimento (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_cds_ativ_col_pratica | - |
| public.tb_cds_ativ_col_publico_alvo | - |
| public.tb_cds_ativ_col_tema | - |
| public.tb_cds_aval_elegibilidade | co_cid10_principal (padrão de nome), co_cid10_segundo (padrão de nome), co_cid10_terceiro (padrão de nome), co_localidade_cidadao (padrão de nome), co_localidade_cidadao_nasc (padrão de nome), co_raca_cor (padrão de nome), tp_logradouro (padrão de nome), ds_complemento (padrão de nome), ds_email_cidadao (padrão de nome), dt_nascimento (padrão de nome), no_bairro (padrão de nome), no_cidadao (padrão de nome), no_logradouro (padrão de nome), no_mae_cidadao (padrão de nome), no_social_cidadao (padrão de nome), nu_cep (padrão de nome), nu_cns_cidadao (padrão de nome), nu_fone_referencia (padrão de nome), nu_fone_residencia (padrão de nome), nu_nis_pis_pasep (padrão de nome), nu_prontuario (padrão de nome), st_desconhece_nome_mae (padrão de nome), co_etnia (padrão de nome), no_pai_cidadao (padrão de nome), st_desconhece_nome_pai (padrão de nome), nu_cns_cuidador (padrão de nome), nu_cpf_cidadao (padrão de nome), nu_cpf_cuidador (padrão de nome) |
| public.tb_cds_cad_domiciliar | tp_logradouro (padrão de nome), no_logradouro (padrão de nome), ds_complemento (padrão de nome), no_bairro (padrão de nome), nu_cep (padrão de nome), nu_fone_residencia (padrão de nome), nu_fone_referencia (padrão de nome), no_logradouro_filtro (padrão de nome), no_responsavel_tecnico (padrão de nome), nu_cns_responsavel_tecnico (padrão de nome), nu_fone_responsavel_tecnico (padrão de nome), ds_complemento_filtro (padrão de nome), nu_latitude (padrão de nome), nu_longitude (padrão de nome), co_tipo_endereco (padrão de nome) |
| public.tb_cds_cad_individual | nu_pis_pasep (padrão de nome), nu_cartao_sus_responsavel (padrão de nome), dt_nascimento_responsavel (padrão de nome), st_responsavel_familiar (padrão de nome), nu_cns_cidadao (padrão de nome), no_cidadao (padrão de nome), no_social_cidadao (padrão de nome), dt_nascimento (padrão de nome), co_raca_cor (padrão de nome), no_mae_cidadao (padrão de nome), st_desconhece_nome_mae (padrão de nome), nu_celular_cidadao (padrão de nome), ds_email_cidadao (padrão de nome), no_cidadao_filtro (padrão de nome), co_etnia (padrão de nome), no_pai_cidadao (padrão de nome), st_desconhece_nome_pai (padrão de nome), nu_declaracao_obito (padrão de nome), nu_cpf_cidadao (padrão de nome), nu_cpf_responsavel (padrão de nome) |
| public.tb_cds_cidadao_resposta | co_seq_cds_cidadao_resposta (padrão de nome) |
| public.tb_cds_domicilio | tp_logradouro (padrão de nome), ds_complemento (padrão de nome), no_logradouro (padrão de nome), no_bairro (padrão de nome), ds_cep (padrão de nome), nu_fone_referencia (padrão de nome), nu_fone_residencia (padrão de nome), no_responsavel_tecnico (padrão de nome), nu_cns_responsavel_tecnico (padrão de nome), nu_contato_responsavel_tecnico (padrão de nome), nu_latitude (padrão de nome), nu_longitude (padrão de nome), no_bairro_filtro (padrão de nome), no_logradouro_filtro (padrão de nome), nu_cns (padrão de nome), co_tipo_endereco (padrão de nome) |
| public.tb_cds_domicilio_familia | nu_prontuario (padrão de nome), dt_nascimento (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_cds_domicilio_resposta | - |
| public.tb_cds_ficha_atend_domiciliar | co_cds_prof_principal (padrão de nome) |
| public.tb_cds_ficha_atend_individual | - |
| public.tb_cds_ficha_atend_odonto | - |
| public.tb_cds_ficha_ativ_col | co_cds_prof_responsavel (padrão de nome) |
| public.tb_cds_ficha_consumo_alimentar | nu_cns_cidadao (padrão de nome), no_identificacao_cidadao (padrão de nome), dt_nascimento_cidadao (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_cds_ficha_proced | - |
| public.tb_cds_ficha_vacinacao | - |
| public.tb_cds_ficha_visita_domiciliar | - |
| public.tb_cds_pic | - |
| public.tb_cds_proced | nu_prontuario (padrão de nome), dt_nascimento (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_cds_prof | nu_cns (padrão de nome) |
| public.tb_cds_tipo_atend_nasf | - |
| public.tb_cds_tipo_ativ_col | - |
| public.tb_cds_tipo_conduta | - |
| public.tb_cds_tipo_cuidador | - |
| public.tb_cds_tipo_imovel | - |
| public.tb_cds_tipo_origem | - |
| public.tb_cds_tipo_situacao_presente | - |
| public.tb_cds_tipo_vig_saude_bucal | - |
| public.tb_cds_turno | - |
| public.tb_cds_vacina | co_cid10_motivo_indicacao (padrão de nome) |
| public.tb_cds_vacinacao | nu_prontuario (padrão de nome), dt_nascimento (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_cds_visita_dom_desfecho | - |
| public.tb_cds_visita_dom_motivo | - |
| public.tb_cds_visita_domiciliar | nu_prontuario (padrão de nome), dt_nascimento (padrão de nome), nu_cpf_cidadao (padrão de nome), nu_latitude (padrão de nome), nu_longitude (padrão de nome) |
| public.tb_cfg_agenda | - |
| public.tb_cfg_agenda_detalhe | - |
| public.tb_cfg_agenda_municipal | nu_duracao_atendimento_padrao (padrão de nome) |
| public.tb_cfg_agenda_online_detalhe | - |
| public.tb_cfg_certificado | ds_senha_certificado (padrão de nome) |
| public.tb_ciap | co_cid10_encaminhamento (padrão de nome), no_sexo (padrão de nome) |
| public.tb_ciap_capitulo | - |
| public.tb_ciap_componente | - |
| public.tb_ciap_dab | - |
| public.tb_ciap_ms | - |
| public.tb_cid10 | co_cid10 (padrão de nome), nu_cid10 (padrão de nome), no_cid10 (padrão de nome), no_cid10_filtro (padrão de nome), no_sexo (padrão de nome), nu_cid10_filtro (padrão de nome) |
| public.tb_cidadao | co_seq_cidadao (padrão de nome), st_desconhece_nome_mae (padrão de nome), nu_nis_pis_pasep (padrão de nome), nu_cns_responsavel (padrão de nome), no_responsavel (padrão de nome), dt_nascimento_responsavel (padrão de nome), nu_cns_cuidador (padrão de nome), no_cuidador (padrão de nome), dt_nascimento_cuidador (padrão de nome), co_unico_cidadao (padrão de nome), co_pais_nascimento (padrão de nome), st_desconhece_nome_pai (padrão de nome), st_infrm_orientacao_sexual (padrão de nome), tp_orientacao_sexual (padrão de nome), st_infrm_identidade_genero (padrão de nome), tp_identidade_genero (padrão de nome), st_compartilhamento_prontuario (padrão de nome), nu_cpf (padrão de nome), nu_cns (padrão de nome), no_cidadao (padrão de nome), no_cidadao_filtro (padrão de nome), co_raca_cor (padrão de nome), co_etnia (padrão de nome), dt_nascimento (padrão de nome), no_mae (padrão de nome), no_mae_filtro (padrão de nome), no_pai (padrão de nome), no_social (padrão de nome), nu_documento_obito (padrão de nome), ds_cep (padrão de nome), ds_complemento (padrão de nome), ds_logradouro (padrão de nome), co_localidade_endereco (padrão de nome), no_bairro (padrão de nome), no_bairro_filtro (padrão de nome), tp_logradouro (padrão de nome), nu_telefone_residencial (padrão de nome), nu_telefone_celular (padrão de nome), nu_telefone_contato (padrão de nome), ds_email (padrão de nome), st_territorio_utiliza_cpf (padrão de nome), nu_cpf_cuidador (padrão de nome), nu_cpf_responsavel (padrão de nome), no_tipo_sanguineo (padrão de nome), no_sexo (padrão de nome), co_tipo_endereco (padrão de nome) |
| public.tb_cidadao_bolsa_familia | co_seq_cidadao_bolsa_familia (padrão de nome), nu_documento (padrão de nome), tp_documento (padrão de nome), no_cidadao (padrão de nome) |
| public.tb_cidadao_grupo | co_seq_cidadao_grupo (padrão de nome), nu_cns (padrão de nome), co_cidadao (padrão de nome), co_cidadao_master (padrão de nome), co_cidadao_unificado (padrão de nome), nu_cpf (padrão de nome) |
| public.tb_cidadao_nucleo_familiar | co_seq_cidadao_nucleo_familiar (padrão de nome), nu_cpf_cns_responsavel (padrão de nome), st_responsavel (padrão de nome), co_cidadao (padrão de nome), nu_cns_profissional (padrão de nome) |
| public.tb_cidadao_vinculacao_equipe | co_seq_cidadao_vinculacao_eqp (padrão de nome), co_cidadao (padrão de nome) |
| public.tb_cirurgias_internacoes | co_prontuario (padrão de nome) |
| public.tb_classe_imunobiologico | - |
| public.tb_classificacao_prioridade_cc | - |
| public.tb_classificacao_risco | - |
| public.tb_classificacao_risco_encam | - |
| public.tb_cnes | - |
| public.tb_complexidade | - |
| public.tb_conduta_cuidado_compartilhd | - |
| public.tb_config_agenda_fechamento | - |
| public.tb_config_atencao_domiciliar | qt_tempo_duracao_consulta (padrão de nome) |
| public.tb_config_sistema | co_config_sistema (PK/FK com tipo não-numérico (possível chave natural)) |
| public.tb_conselho_classe | - |
| public.tb_contexto_pergunta | - |
| public.tb_criticidade_alergia | co_criticidade_alergia (padrão de nome), no_criticidade_alergia (padrão de nome) |
| public.tb_cronicidade | - |
| public.tb_cuidado_compartilhado | co_prontuario (padrão de nome), co_cid10 (padrão de nome), st_cidadao_aceita_atend_tic (padrão de nome) |
| public.tb_cuidado_compartilhado_evol | - |
| public.tb_cuidado_finalizacao_auto | - |
| public.tb_dado_recebido_competencia | - |
| public.tb_dado_recebido_info_instalac | nu_identificador_responsavel (padrão de nome), no_responsavel_envio (padrão de nome), nu_telefone (padrão de nome), ds_email (padrão de nome) |
| public.tb_dado_rel_processamento | dt_att_cidadao_pec_etl (padrão de nome) |
| public.tb_dado_transp | - |
| public.tb_dado_transp_recebido | - |
| public.tb_dente | - |
| public.tb_dia_semana | - |
| public.tb_dim_agrupador_filtro | co_dim_profissional (padrão de nome) |
| public.tb_dim_aldeia | - |
| public.tb_dim_aleitamento | - |
| public.tb_dim_catmat | ds_concentracao (padrão de nome) |
| public.tb_dim_cbo | - |
| public.tb_dim_ciap | - |
| public.tb_dim_cid | co_seq_dim_cid (padrão de nome), nu_cid (padrão de nome), no_cid (padrão de nome) |
| public.tb_dim_cidadao_pec_grupo | co_seq_dim_cidadao_pec_grupo (padrão de nome), co_fat_cidadao_pec (padrão de nome), co_cidadao (padrão de nome), co_cidadao_master (padrão de nome) |
| public.tb_dim_classificacao_risc_enc | - |
| public.tb_dim_condicao_maternal | - |
| public.tb_dim_conduta_ad | - |
| public.tb_dim_conduta_cuidado | - |
| public.tb_dim_cuidador | - |
| public.tb_dim_desfecho_visita | - |
| public.tb_dim_dose_frequencia | - |
| public.tb_dim_dose_frequencia_medida | - |
| public.tb_dim_dose_imunobiologico | - |
| public.tb_dim_dsei | - |
| public.tb_dim_duracao_tratamento_med | co_seq_dim_duracao_trat_med (padrão de nome), nu_duracao_tratamento_med (padrão de nome), no_duracao_tratamento_med (padrão de nome), no_duracao_tratamento_med_filt (padrão de nome) |
| public.tb_dim_equipe | - |
| public.tb_dim_especialidade | - |
| public.tb_dim_estrategia_vacinacao | - |
| public.tb_dim_etnia | co_seq_dim_etnia (padrão de nome), no_etnia (padrão de nome) |
| public.tb_dim_faixa_etaria | - |
| public.tb_dim_forma_farmaceutica | - |
| public.tb_dim_frequencia_alimentacao | - |
| public.tb_dim_grau_vulnerabilidade | - |
| public.tb_dim_grupo_atendimento | - |
| public.tb_dim_grupo_cbo | - |
| public.tb_dim_identidade_genero | co_seq_dim_identidade_genero (padrão de nome), ds_identidade_genero (padrão de nome) |
| public.tb_dim_imunobiologico | - |
| public.tb_dim_inep | - |
| public.tb_dim_local_atendimento | - |
| public.tb_dim_modalidade_ad | - |
| public.tb_dim_municipio | no_municipio (padrão de nome) |
| public.tb_dim_nacionalidade | - |
| public.tb_dim_pais | - |
| public.tb_dim_pic | - |
| public.tb_dim_polo_base | - |
| public.tb_dim_povo_comunidad_trad | - |
| public.tb_dim_prioridade_cuidado | - |
| public.tb_dim_procedencia_origem | - |
| public.tb_dim_procedimento | - |
| public.tb_dim_profissional | co_seq_dim_profissional (padrão de nome), nu_cns (padrão de nome), no_profissional (padrão de nome) |
| public.tb_dim_raca_cor | co_seq_dim_raca_cor (padrão de nome), ds_raca_cor (padrão de nome) |
| public.tb_dim_racionalidade_saude | - |
| public.tb_dim_sexo | - |
| public.tb_dim_situacao_problema | - |
| public.tb_dim_situacao_trabalho | - |
| public.tb_dim_tempo | - |
| public.tb_dim_tempo_morador_rua | - |
| public.tb_dim_tipo_abastecimento_agua | - |
| public.tb_dim_tipo_acesso_domicilio | - |
| public.tb_dim_tipo_atendimento | - |
| public.tb_dim_tipo_atividade | - |
| public.tb_dim_tipo_condicao_peso | - |
| public.tb_dim_tipo_consulta_odonto | co_seq_dim_tipo_cnsulta_odonto (padrão de nome) |
| public.tb_dim_tipo_destino_lixo | - |
| public.tb_dim_tipo_domicilio | - |
| public.tb_dim_tipo_elegibilidade | - |
| public.tb_dim_tipo_endereco | co_seq_dim_tipo_endereco (padrão de nome), ds_tipo_endereco (padrão de nome) |
| public.tb_dim_tipo_escoamento_sanitar | - |
| public.tb_dim_tipo_escolaridade | - |
| public.tb_dim_tipo_ficha | - |
| public.tb_dim_tipo_glicemia | - |
| public.tb_dim_tipo_imovel | - |
| public.tb_dim_tipo_localizacao | - |
| public.tb_dim_tipo_logradouro | co_seq_dim_tipo_logradouro (padrão de nome), ds_tipo_logradouro (padrão de nome) |
| public.tb_dim_tipo_material_parede | - |
| public.tb_dim_tipo_orientacao_sexual | ds_dim_tipo_orientacao_sexual (padrão de nome) |
| public.tb_dim_tipo_origem | - |
| public.tb_dim_tipo_origem_dado_transp | - |
| public.tb_dim_tipo_origem_energ_elet | - |
| public.tb_dim_tipo_parentesco | - |
| public.tb_dim_tipo_participacao_atend | - |
| public.tb_dim_tipo_posse_terra | - |
| public.tb_dim_tipo_renda_familiar | - |
| public.tb_dim_tipo_saida_cadastro | - |
| public.tb_dim_tipo_situacao_moradia | - |
| public.tb_dim_tipo_tratamento_agua | - |
| public.tb_dim_turno | - |
| public.tb_dim_uf | - |
| public.tb_dim_unidade_saude | no_bairro (padrão de nome) |
| public.tb_dim_via_administracao | co_seq_dim_via_administracao (padrão de nome), no_via_administracao (padrão de nome), no_via_administracao_filtro (padrão de nome) |
| public.tb_dim_vinculacao_equipes | co_dim_equipe_principal (padrão de nome) |
| public.tb_dim_zika_tipo_exame | - |
| public.tb_dose_imunobiologico | - |
| public.tb_dsei | no_dsei (padrão de nome), no_dsei_filtro (padrão de nome), ds_email (padrão de nome), ds_email_chefe (padrão de nome), no_chefe_dsei (padrão de nome), no_logradouro (padrão de nome), no_bairro (padrão de nome), nu_cep (padrão de nome), ds_complemento (padrão de nome), nu_telefone1 (padrão de nome), nu_telefone2 (padrão de nome) |
| public.tb_encaminhamento | co_prontuario (padrão de nome), ds_complemento (padrão de nome), co_cid10 (padrão de nome) |
| public.tb_envio_rnds | nu_cns_prof (padrão de nome) |
| public.tb_equipe | - |
| public.tb_escolaridade | - |
| public.tb_especialidade_sisreg | - |
| public.tb_estado_civil | - |
| public.tb_estrategia_vacinacao | - |
| public.tb_etl_auxiliar_number | - |
| public.tb_etnia | co_etnia (padrão de nome), no_etnia (padrão de nome), co_etnia_cadsus (padrão de nome) |
| public.tb_evolucao_avaliacao | - |
| public.tb_evolucao_dente | - |
| public.tb_evolucao_objetivo | - |
| public.tb_evolucao_odonto | co_prontuario (padrão de nome) |
| public.tb_evolucao_plano | - |
| public.tb_evolucao_subjetivo | - |
| public.tb_exame_clearance_creatina | - |
| public.tb_exame_colesterol_hdl | - |
| public.tb_exame_colesterol_ldl | - |
| public.tb_exame_colesterol_total | - |
| public.tb_exame_creatina_serica | - |
| public.tb_exame_detalhe | - |
| public.tb_exame_hemoglobina_glicada | - |
| public.tb_exame_prenatal | - |
| public.tb_exame_puericultura | - |
| public.tb_exame_requisitado | co_prontuario (padrão de nome) |
| public.tb_exame_triglicerideos | - |
| public.tb_faixa_etaria_vacinacao | - |
| public.tb_familia | nu_cpf_cns_responsavel (padrão de nome), nu_prontuario_familiar (padrão de nome), dt_nascimento_responsavel (padrão de nome), st_responsavel_cadastrado (padrão de nome), st_responsavel_declarado (padrão de nome), st_responsavel_vivo (padrão de nome), st_responsavel_unico (padrão de nome), st_responsavel_ainda_reside (padrão de nome) |
| public.tb_fat_atd_ind_encaminhamentos | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns_cidadao (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome), co_dim_cid10 (padrão de nome) |
| public.tb_fat_atd_ind_exames | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns_cidadao (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_fat_atd_ind_medicamentos | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns_cidadao (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome), co_dim_duracao_tratamento_med (padrão de nome), co_dim_via_administracao (padrão de nome), qt_duracao_tratamento (padrão de nome) |
| public.tb_fat_atd_ind_problemas | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns (padrão de nome), co_dim_cid (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_fat_atd_ind_procedimentos | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_fat_atend_dom_prob_cond | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), co_dim_cid (padrão de nome) |
| public.tb_fat_atend_dom_proced | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome) |
| public.tb_fat_atend_odonto_encaminham | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns_cidadao (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome), co_dim_cid10 (padrão de nome) |
| public.tb_fat_atend_odonto_exames | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns_cidadao (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_fat_atend_odonto_medicament | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns_cidadao (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome), co_dim_duracao_tratamento_med (padrão de nome), co_dim_via_administracao (padrão de nome), qt_duracao_tratamento (padrão de nome) |
| public.tb_fat_atend_odonto_problemas | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns (padrão de nome), co_dim_cid (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_fat_atend_odonto_proced | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_fat_atendimento_domiciliar | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns (padrão de nome), dt_nascimento (padrão de nome), ds_filtro_cids (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_fat_atendimento_individual | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns (padrão de nome), dt_nascimento (padrão de nome), st_nasf_avaliacao_diagnostico (padrão de nome), ds_filtro_cids (padrão de nome), nu_prontuario (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome), co_dim_tp_particip_cidadao (padrão de nome), nu_saturacao_o2 (padrão de nome) |
| public.tb_fat_atendimento_odonto | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns (padrão de nome), dt_nascimento (padrão de nome), st_gestante (padrão de nome), ds_filtro_cids (padrão de nome), nu_prontuario (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome), co_dim_tp_particip_cidadao (padrão de nome), nu_saturacao_o2 (padrão de nome) |
| public.tb_fat_atividade_coletiva | co_dim_profissional (padrão de nome) |
| public.tb_fat_atvdd_coletiva_ext | co_dim_profissional (padrão de nome), st_pblc_alvo_gestante (padrão de nome), st_pblc_alvo_usuario_tabaco (padrão de nome), st_pblc_alvo_usuario_alcool (padrão de nome), st_pblc_alvo_usuario_outr_drog (padrão de nome), st_tema_saude_cidad_dirt_human (padrão de nome) |
| public.tb_fat_atvdd_coletiva_int | co_dim_profissional (padrão de nome), st_tema_saude_cidad_dirt_human (padrão de nome) |
| public.tb_fat_atvdd_coletiva_part | co_dim_profissional (padrão de nome), nu_participante_cns (padrão de nome), dt_participante_nascimento (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_participante (padrão de nome) |
| public.tb_fat_atvdd_coletiva_propart | co_dim_profissional (padrão de nome) |
| public.tb_fat_avaliacao_elegibilidade | co_dim_profissional_1 (padrão de nome), co_dim_profissional_2 (padrão de nome), nu_cns (padrão de nome), dt_nascimento (padrão de nome), co_dim_cid_principal (padrão de nome), co_dim_cid_sec_1 (padrão de nome), co_dim_cid_sec_2 (padrão de nome), co_dim_raca_cor (padrão de nome), co_dim_etnia (padrão de nome), st_desconhece_nome_mae (padrão de nome), st_desconhece_nome_pai (padrão de nome), co_dim_pais_nascimento (padrão de nome), co_dim_municipio_cidadao (padrão de nome), co_dim_tipo_logradouro (padrão de nome), nu_cns_cuidador (padrão de nome), no_nome (padrão de nome), no_nome_social (padrão de nome), nu_nis (padrão de nome), no_nome_mae (padrão de nome), no_nome_pai (padrão de nome), co_dim_uf_cidadao (padrão de nome), no_email (padrão de nome), nu_cep_residencia (padrão de nome), no_bairro_residencia (padrão de nome), no_logradouro_residencia (padrão de nome), nu_num_logradouro_residencia (padrão de nome), no_complemento_residencia (padrão de nome), nu_telefone_residencia (padrão de nome), nu_telefone_contato (padrão de nome), co_fat_cidadao_pec (padrão de nome), co_fat_cidadao_pec_cuidador (padrão de nome), nu_cpf_cidadao (padrão de nome), nu_cpf_cuidador (padrão de nome) |
| public.tb_fat_cad_dom_familia | co_dim_profissional (padrão de nome), nu_cns_responsavel (padrão de nome), dt_nascimento (padrão de nome), nu_prontuario (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_responsavel (padrão de nome) |
| public.tb_fat_cad_domiciliar | co_dim_profissional (padrão de nome), co_dim_tipo_logradouro (padrão de nome), co_dim_municipio_cidadao (padrão de nome), nu_cep (padrão de nome), no_logradouro (padrão de nome), nu_num_logradouro (padrão de nome), no_complemento (padrão de nome), no_bairro (padrão de nome), nu_telefone_residencia (padrão de nome), nu_telefone_contato (padrão de nome), no_instituicao_nome (padrão de nome), nu_instituicao_cns (padrão de nome), nu_instituicao_telefone (padrão de nome), nu_latitude (padrão de nome), nu_longitude (padrão de nome), co_dim_tipo_endereco (padrão de nome) |
| public.tb_fat_cad_individual | nu_cns (padrão de nome), dt_nascimento (padrão de nome), co_dim_profissional (padrão de nome), co_dim_raca_cor (padrão de nome), co_dim_pais_nascimento (padrão de nome), co_dim_municipio_cidadao (padrão de nome), nu_cns_responsavel (padrão de nome), st_responsavel_familiar (padrão de nome), st_gestante (padrão de nome), st_doenca_respiratoria (padrão de nome), st_doenca_respira_asma (padrão de nome), st_doenca_respira_dpoc_enfisem (padrão de nome), st_doenca_respira_outra (padrão de nome), st_doenca_respira_n_sabe (padrão de nome), st_doenca_cardiaca (padrão de nome), st_doenca_card_insuficiencia (padrão de nome), st_doenca_card_outro (padrão de nome), st_doenca_card_n_sabe (padrão de nome), co_dim_tipo_orientacao_sexual (padrão de nome), co_dim_etnia (padrão de nome), co_dim_cbo_cidadao (padrão de nome), co_dim_identidade_genero (padrão de nome), st_informar_orientacao_sexual (padrão de nome), st_informar_identidade_genero (padrão de nome), st_processo_cidadao (padrão de nome), no_nome (padrão de nome), no_nome_social (padrão de nome), no_nome_mae (padrão de nome), no_nome_pai (padrão de nome), nu_nis (padrão de nome), nu_celular (padrão de nome), no_email (padrão de nome), co_fat_cidadao_pec (padrão de nome), co_fat_cidadao_pec_responsvl (padrão de nome), nu_cpf_cidadao (padrão de nome), nu_cpf_responsavel (padrão de nome) |
| public.tb_fat_cidadao | co_seq_fat_cidadao (padrão de nome), nu_cns (padrão de nome), co_fat_cidadao_raiz (padrão de nome), co_fat_cidadao_pai1 (padrão de nome), co_fat_cidadao_pai2 (padrão de nome), co_fat_cidadao_raiz_equipe (padrão de nome), co_fat_cidadao_pai1_equipe (padrão de nome), co_fat_cidadao_pai2_equipe (padrão de nome), co_fat_cidadao_raiz_undde_sade (padrão de nome), co_fat_cidadao_pai1_undde_sade (padrão de nome), co_fat_cidadao_pai2_undde_sade (padrão de nome), co_fat_cidadao_raiz_municipio (padrão de nome), co_fat_cidadao_pai1_municipio (padrão de nome), co_fat_cidadao_pai2_municipio (padrão de nome), st_responsavel_familiar (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_fat_cidadao_pec | co_seq_fat_cidadao_pec (padrão de nome), co_cidadao (padrão de nome), nu_cns (padrão de nome), no_cidadao (padrão de nome), no_social_cidadao (padrão de nome), co_dim_tempo_nascimento (padrão de nome), co_dim_identidade_genero (padrão de nome), nu_telefone_celular (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_fat_cidadao_territorio | co_seq_fat_cidadao_territorio (padrão de nome), co_fat_cidadao_pec (padrão de nome), st_responsavel (padrão de nome), st_responsavel_informado (padrão de nome), st_responsavel_com_fci (padrão de nome), st_cns_null (padrão de nome), st_cidadao_consistente (padrão de nome), co_fat_ciddo_terrtrio_resp (padrão de nome), st_processado_cidadao_respnsvl (padrão de nome) |
| public.tb_fat_cnslddo_ciddo_fai_cid | co_seq_fat_cnsldo_cido_fai_cid (padrão de nome), co_fat_cidadao_pec (padrão de nome), co_dim_cid (padrão de nome) |
| public.tb_fat_consolidado_cidadao_fad | co_seq_fat_conslddo_ciddo_fad (padrão de nome), co_fat_cidadao_pec (padrão de nome) |
| public.tb_fat_consolidado_cidadao_fai | co_seq_fat_conslddo_ciddo_fai (padrão de nome), co_fat_cidadao_pec (padrão de nome), co_dim_tempo_doenca_cardiaca (padrão de nome), co_dim_tempo_cnslta_1_prcltra (padrão de nome) |
| public.tb_fat_consolidado_cidadao_fao | co_seq_fat_conslddo_ciddo_fao (padrão de nome), co_fat_cidadao_pec (padrão de nome) |
| public.tb_fat_consolidado_cidadao_fci | co_seq_fat_conslddo_ciddo_fci (padrão de nome), co_fat_cidadao_pec (padrão de nome), dt_nascimento (padrão de nome) |
| public.tb_fat_consolidado_cidadao_fp | co_seq_fat_conslddo_ciddo_fp (padrão de nome), co_fat_cidadao_pec (padrão de nome) |
| public.tb_fat_consolidado_cidadao_fvd | co_seq_fat_conslddo_ciddo_fvd (padrão de nome), co_fat_cidadao_pec (padrão de nome) |
| public.tb_fat_cuidado_compartilhado | co_dim_profissional_evolucao (padrão de nome), nu_cns_cidadao (padrão de nome), nu_cpf_cidadao (padrão de nome), co_fat_cidadao_pec (padrão de nome), co_dim_sexo_cidadao (padrão de nome), dt_nascimento_cidadao (padrão de nome), co_dim_profissional_solicitant (padrão de nome), co_dim_profissional_executante (padrão de nome), co_dim_cid (padrão de nome) |
| public.tb_fat_familia | co_fat_cidadao (padrão de nome), nu_cns_responsavel (padrão de nome), st_responsavel_declarado_ci (padrão de nome), st_responsavel_vivo (padrão de nome), st_responsavel_unico (padrão de nome), st_responsavel_ainda_reside (padrão de nome), nu_cpf_responsavel (padrão de nome) |
| public.tb_fat_familia_territorio | co_fat_cidadao_pec (padrão de nome), nu_prontuario (padrão de nome), st_responsavel_ainda_reside (padrão de nome), st_responsavel_vivo (padrão de nome), st_processo_att_cidadao (padrão de nome), co_fat_cidadao_territorio (padrão de nome) |
| public.tb_fat_fichas | - |
| public.tb_fat_ivcf | co_dim_profissional (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cns_cidadao (padrão de nome), nu_cpf_cidadao (padrão de nome), st_sg_percepcao_saude (padrão de nome) |
| public.tb_fat_marca_consumo_alimnt | co_dim_profissional (padrão de nome), nu_cns (padrão de nome), dt_nascimento (padrão de nome), no_nome (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_fat_op_acompanhamento_idosa | co_fat_cidadao_pec (padrão de nome) |
| public.tb_fat_proced_atend | co_dim_profissional (padrão de nome), nu_cns (padrão de nome), dt_nascimento (padrão de nome), nu_prontuario (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome), nu_saturacao_o2 (padrão de nome) |
| public.tb_fat_proced_atend_proced | co_dim_profissional (padrão de nome), nu_cns (padrão de nome), dt_nascimento (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_fat_procedimento | co_dim_profissional (padrão de nome) |
| public.tb_fat_rel_op_crianca | co_fat_cidadao_pec (padrão de nome) |
| public.tb_fat_rel_op_gestante | co_seq_fat_rel_op_gestante (padrão de nome), co_fat_cidadao_pec (padrão de nome) |
| public.tb_fat_rel_op_risco_cardio | co_fat_cidadao_pec (padrão de nome) |
| public.tb_fat_vacinacao | co_dim_profissional (padrão de nome), nu_prontuario (padrão de nome), nu_cns (padrão de nome), dt_nascimento (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tb_fat_vacinacao_vacina | co_dim_profissional (padrão de nome), co_dim_cid_motivo_indicacao (padrão de nome) |
| public.tb_fat_visita_domiciliar | co_dim_profissional (padrão de nome), nu_cns (padrão de nome), dt_nascimento (padrão de nome), st_acomp_gestante (padrão de nome), st_acomp_pessoa_doenca_cronica (padrão de nome), st_acomp_usuario_alcool (padrão de nome), st_acomp_usuario_outras_drogra (padrão de nome), nu_prontuario (padrão de nome), co_fat_cidadao_pec (padrão de nome), nu_cpf_cidadao (padrão de nome), nu_latitude (padrão de nome), nu_longitude (padrão de nome) |
| public.tb_ficha_zika_tipo_exame | - |
| public.tb_forma_farmaceutica | - |
| public.tb_funcao_social | - |
| public.tb_gestor_municipal | - |
| public.tb_grau_certeza_alergia | co_seq_grau_certeza_alergia (padrão de nome), no_grau_certeza_alergia (padrão de nome) |
| public.tb_grau_parentesco | - |
| public.tb_gravidade | - |
| public.tb_grupo_alvo_vacinacao | - |
| public.tb_grupo_atendimento | - |
| public.tb_grupo_ativ_col | - |
| public.tb_grupo_condicao_saude | co_seq_grupo_condicao_saude (padrão de nome) |
| public.tb_grupo_especialidade | - |
| public.tb_grupo_exame | no_sexo (padrão de nome) |
| public.tb_historico_acesso | co_usuario (padrão de nome) |
| public.tb_historico_cabecalho | nu_cpf_cns_cidadao (padrão de nome), nu_cns_prof (padrão de nome), co_prontuario (padrão de nome), nu_cpf_estagiario (padrão de nome) |
| public.tb_historico_dados_exames | nu_cpf_cns_cidadao (padrão de nome) |
| public.tb_historico_dados_fad | nu_cpf_cns_cidadao (padrão de nome), ds_ciap_nome_codigo (padrão de nome), ds_cid_nome_codigo (padrão de nome) |
| public.tb_historico_dados_fae | ds_cid10_principal (padrão de nome), ds_cid10_secundario_um (padrão de nome), ds_cid10_secundario_dois (padrão de nome) |
| public.tb_historico_dados_fai | nu_cpf_cns_cidadao (padrão de nome), ds_ciap_nome_codigo (padrão de nome), ds_cid_nome_codigo (padrão de nome), no_nome_finalizador_obs (padrão de nome), nu_cns_finalizador_obs (padrão de nome) |
| public.tb_historico_dados_fao | nu_cpf_cns_cidadao (padrão de nome), ds_ciap_nome_codigo (padrão de nome), ds_cid_nome_codigo (padrão de nome) |
| public.tb_historico_dados_fcc | nu_cpf_cns_cidadao (padrão de nome), ds_ciap_nome (padrão de nome), ds_cid_nome (padrão de nome), ds_cid_codigo (padrão de nome), nu_cns_solicitante (padrão de nome), no_nome_solicitante (padrão de nome), nu_cns_executante (padrão de nome), no_nome_executante (padrão de nome) |
| public.tb_historico_dados_proced | nu_cpf_cns_cidadao (padrão de nome), ds_proced_nome_codigo (padrão de nome) |
| public.tb_historico_dados_tags | st_atestado (padrão de nome), st_medicamento (padrão de nome), st_alergia (padrão de nome), st_resultado_exame (padrão de nome) |
| public.tb_historico_dados_vacina | nu_cpf_cns_cidadao (padrão de nome), ds_vacina_nome_sigla (padrão de nome) |
| public.tb_historico_unificacao | co_cidadao_grupo (padrão de nome) |
| public.tb_importacao_bolsa_familia | - |
| public.tb_importacao_cnes | ds_detalhes (padrão de nome) |
| public.tb_imunobiologico | - |
| public.tb_imunobiologico_fabricante | - |
| public.tb_imunobiologico_lote | - |
| public.tb_inep | - |
| public.tb_ivcf | co_prontuario (padrão de nome), st_sg_percepcao_saude (padrão de nome) |
| public.tb_ivcf_aplicacao | - |
| public.tb_ivcf_perguntas | - |
| public.tb_justificativa_agenda | co_responsavel_cancelamento (padrão de nome), co_usuario (padrão de nome) |
| public.tb_justificativa_prontuario | dt_acesso_prontuario (padrão de nome), co_prontuario (padrão de nome), co_usuario (padrão de nome) |
| public.tb_lembrete | co_prontuario (padrão de nome) |
| public.tb_lembrete_evolucao | dt_prontuario_lembrete (padrão de nome) |
| public.tb_lista_espera_motivo_saida | - |
| public.tb_lista_espera_tipo_atend | - |
| public.tb_lista_medicamento | co_lista_medicamento (padrão de nome), tp_lista_medicamento (padrão de nome), ds_lista_medicamento (padrão de nome) |
| public.tb_local_apl_vacina | - |
| public.tb_local_atend | - |
| public.tb_local_ocorrencia | - |
| public.tb_localidade | nu_cep (padrão de nome) |
| public.tb_logradouro | co_logradouro (padrão de nome), no_logradouro (padrão de nome), nu_cep (padrão de nome), tp_logradouro (padrão de nome), no_logradouro_filtro (padrão de nome), no_logradouro_exibicao (padrão de nome), no_complemento (padrão de nome), ds_letra_numero_complemento (padrão de nome), co_bairro_dne (PK/FK com tipo não-numérico (possível chave natural)) |
| public.tb_lotacao | - |
| public.tb_lote_transp | - |
| public.tb_lote_transp_historico_exprt | no_profissional (padrão de nome) |
| public.tb_lote_transp_item | - |
| public.tb_lote_transp_item_nodo | - |
| public.tb_lote_transp_nodo | - |
| public.tb_manifestacao_alergia | co_seq_manifestacao_alergia (padrão de nome), no_manifestacao_alergia (padrão de nome), no_filtro_manifestacao_alergia (padrão de nome) |
| public.tb_marcador_consumo_alimentar | - |
| public.tb_mchat | co_prontuario (padrão de nome) |
| public.tb_mchat_aplicacao | - |
| public.tb_mchat_pergunta | - |
| public.tb_medicamento | co_seq_medicamento (padrão de nome), ds_concentracao (padrão de nome) |
| public.tb_medicamento_catmat | co_medicamento_catmat (padrão de nome), co_medicamento (padrão de nome), no_medicamento_filtro (padrão de nome) |
| public.tb_medicamento_uso_continuo | co_medicamento (padrão de nome), co_prontuario (padrão de nome), co_ultima_receita_medicamento (padrão de nome) |
| public.tb_medicao | nu_medicao_saturacao_o2 (padrão de nome) |
| public.tb_migracao | - |
| public.tb_migracao_estrutura | co_migracao_estrutura (padrão de nome), no_autor_migracao (padrão de nome), no_arquivo_migracao (padrão de nome) |
| public.tb_migracao_trava | - |
| public.tb_modelo_personalizado | co_seq_modelo_personalizado (padrão de nome), no_modelo (padrão de nome), ds_modelo_personalizado (padrão de nome) |
| public.tb_motivo_reserva | co_motivo_reserva (padrão de nome), no_motivo_reserva (padrão de nome) |
| public.tb_nacionalidade | - |
| public.tb_neuro_alter_fenot | co_prontuario (padrão de nome) |
| public.tb_neuro_alter_fenot_detalhe | - |
| public.tb_neuro_alter_fenot_evolucao | - |
| public.tb_neuro_faixa_etaria | - |
| public.tb_neuro_fator_risco | co_prontuario (padrão de nome) |
| public.tb_neuro_fator_risco_detalhe | - |
| public.tb_neuro_fator_risco_evolucao | - |
| public.tb_neuro_marco | co_prontuario (padrão de nome) |
| public.tb_neuro_marco_detalhe | - |
| public.tb_neuro_marco_evolucao | - |
| public.tb_nodo | ds_nome (padrão de nome) |
| public.tb_notificacao_status | - |
| public.tb_odontograma | co_prontuario (padrão de nome) |
| public.tb_opcoes_result_exm_qlitativo | - |
| public.tb_orientacao | co_prontuario (padrão de nome) |
| public.tb_origem | - |
| public.tb_pais | - |
| public.tb_parte_bucal | - |
| public.tb_parte_bucal_cid10 | co_parte_bucal_cid10 (padrão de nome), co_cid10 (padrão de nome) |
| public.tb_parte_bucal_proced | - |
| public.tb_perfil | - |
| public.tb_perfil_recurso | - |
| public.tb_pergunta | - |
| public.tb_pergunta_detalhe | - |
| public.tb_periodo | - |
| public.tb_periograma_simplificado | co_prontuario (padrão de nome) |
| public.tb_polo_base | no_polo_base (padrão de nome), no_polo_base_filtro (padrão de nome), no_bairro (padrão de nome), no_logradouro (padrão de nome), nu_cep (padrão de nome), ds_complemento (padrão de nome), nu_telefone1 (padrão de nome), nu_telefone2 (padrão de nome), ds_email (padrão de nome), no_chefe_polo_base (padrão de nome), ds_email_chefe (padrão de nome) |
| public.tb_povo_comunidade_tradicional | - |
| public.tb_pratica_saude | - |
| public.tb_pre_natal | co_prontuario (padrão de nome) |
| public.tb_principio_ativo | co_lista_medicamento (padrão de nome) |
| public.tb_problema | co_cid10 (padrão de nome), co_prontuario (padrão de nome) |
| public.tb_problema_evolucao | st_possui_cid (padrão de nome) |
| public.tb_proced | - |
| public.tb_proced_automatico | - |
| public.tb_proced_exame_especifico | - |
| public.tb_proced_filtro | - |
| public.tb_proced_forma_organizacional | - |
| public.tb_proced_grupo | - |
| public.tb_proced_subgrupo | - |
| public.tb_processamento_dom_cid | co_seq_processamento_dom_cid (padrão de nome) |
| public.tb_processamento_hist_cds | - |
| public.tb_processamento_historico | - |
| public.tb_processo | - |
| public.tb_prof | nu_cpf (padrão de nome), nu_cns (padrão de nome), no_profissional_filtro (padrão de nome), dt_nascimento (padrão de nome), nu_telefone (padrão de nome), ds_email (padrão de nome), ds_cep (padrão de nome), ds_complemento (padrão de nome), ds_logradouro (padrão de nome), co_localidade_endereco (padrão de nome), no_bairro (padrão de nome), no_bairro_filtro (padrão de nome), tp_logradouro (padrão de nome), co_usuario (padrão de nome), no_sexo (padrão de nome), no_social_profissional (padrão de nome), no_civil_profissional (padrão de nome) |
| public.tb_prof_historico_cns | co_seq_prof_historico_cns (padrão de nome), nu_cns (padrão de nome) |
| public.tb_prontuario | co_seq_prontuario (padrão de nome), co_prontuario_grupo (padrão de nome), co_cidadao (padrão de nome), st_cidadao_processado (padrão de nome) |
| public.tb_prontuario_grupo_historico | co_seq_prontuario_grpo_hstrco (padrão de nome), co_prontuario_grupo (padrão de nome), co_prontuario (padrão de nome) |
| public.tb_publico_alvo | - |
| public.tb_qst_associacao_pergunta | - |
| public.tb_qst_opcao_pergunta | - |
| public.tb_qst_opcao_tipo_pergunta | - |
| public.tb_qst_orientacao_prof | - |
| public.tb_qst_pergunta | - |
| public.tb_qst_questionario | - |
| public.tb_qst_questionario_pergunta | - |
| public.tb_qst_questionario_respondido | - |
| public.tb_qst_resposta | - |
| public.tb_qst_tipo_questionario | - |
| public.tb_qst_tipo_resposta | - |
| public.tb_raca_cor | co_raca_cor (padrão de nome), no_raca_cor (padrão de nome), co_raca_cor_cadsus (padrão de nome) |
| public.tb_racionalidade_saude | - |
| public.tb_recebimento_item | - |
| public.tb_recebimento_lote | no_responsavel_envio (padrão de nome), no_responsavel_envio_filtro (padrão de nome), nu_identificador_responsavel (padrão de nome) |
| public.tb_recebimento_validacao_erros | - |
| public.tb_receita_medicamento | co_seq_receita_medicamento (padrão de nome), co_aplicacao_medicamento (padrão de nome), co_medicamento (padrão de nome), qt_duracao_tratamento (padrão de nome) |
| public.tb_receita_tipo_frequencia | - |
| public.tb_recurso | - |
| public.tb_recurso_credencial_integ | - |
| public.tb_refresh_token | co_token (padrão de nome), no_principal (padrão de nome), dt_expiracao (padrão de nome) |
| public.tb_registro_vacinacao | co_cid10_motivo_indicacao (padrão de nome) |
| public.tb_regra_vacinal_dose | st_gestante (padrão de nome) |
| public.tb_regra_vacinal_estrategia | - |
| public.tb_rel_fichas_config | - |
| public.tb_relatorio_processamento | - |
| public.tb_renda_familiar | - |
| public.tb_report_etl_configs | co_chave (PK/FK com tipo não-numérico (possível chave natural)) |
| public.tb_requisicao_exame | co_cid10 (padrão de nome) |
| public.tb_resposta_mca | - |
| public.tb_retificacao_atend | co_prontuario (padrão de nome) |
| public.tb_revisao | nu_cns (padrão de nome), co_usuario (padrão de nome) |
| public.tb_sessao_sincronizacao | co_unico_sessao (PK/FK com tipo não-numérico (possível chave natural)), co_usuario (padrão de nome) |
| public.tb_sexo | no_sexo (padrão de nome) |
| public.tb_sextante | - |
| public.tb_sinan_notificacao | co_cid10_principal (padrão de nome), no_sexo (padrão de nome) |
| public.tb_sinan_notificacao_evolucao | co_prontuario (padrão de nome) |
| public.tb_situacao_agendado | - |
| public.tb_situacao_coroa | - |
| public.tb_situacao_dado_recebido | - |
| public.tb_situacao_face | - |
| public.tb_situacao_localidade | - |
| public.tb_situacao_lote_transp_nodo | - |
| public.tb_situacao_problema | - |
| public.tb_situacao_raiz | - |
| public.tb_status_assinatura | - |
| public.tb_status_atend | - |
| public.tb_status_atend_prof | - |
| public.tb_status_cuidado_compartilhad | - |
| public.tb_status_revisao_atend | - |
| public.tb_substancia_cbara | co_seq_substancia_alergia (padrão de nome), co_cat_substancia_alergia (padrão de nome), no_substancia_alergia (padrão de nome), no_filtro_substancia_alergia (padrão de nome) |
| public.tb_substancia_espec_alergia | co_seq_substanc_espec_alergia (padrão de nome), co_medicamento_catmat (padrão de nome) |
| public.tb_subtipo_unidade_saude | - |
| public.tb_tecido_mole | co_prontuario (padrão de nome), co_cid10 (padrão de nome) |
| public.tb_tecido_mole_lesao | - |
| public.tb_tema_reuniao | - |
| public.tb_tema_saude | - |
| public.tb_terra_indigena | - |
| public.tb_tipo_abastecimento_agua | - |
| public.tb_tipo_acesso_domicilio | - |
| public.tb_tipo_agendamento | - |
| public.tb_tipo_agravo | - |
| public.tb_tipo_area | - |
| public.tb_tipo_atend | - |
| public.tb_tipo_atend_prof | - |
| public.tb_tipo_atividade | - |
| public.tb_tipo_cfg_agenda | - |
| public.tb_tipo_ciap | - |
| public.tb_tipo_config_atend_domicilir | - |
| public.tb_tipo_consulta_odonto | - |
| public.tb_tipo_dado_transp | - |
| public.tb_tipo_destino_lixo | - |
| public.tb_tipo_domicilio | - |
| public.tb_tipo_edema | - |
| public.tb_tipo_encam_interno | - |
| public.tb_tipo_encam_odonto | - |
| public.tb_tipo_endereco | co_tipo_endereco (padrão de nome), no_tipo_endereco (padrão de nome) |
| public.tb_tipo_equipe | - |
| public.tb_tipo_escoamento_sanitar | - |
| public.tb_tipo_exame | - |
| public.tb_tipo_fornec_odonto | - |
| public.tb_tipo_glicemia | - |
| public.tb_tipo_gravidez | - |
| public.tb_tipo_localidade | - |
| public.tb_tipo_localizacao | - |
| public.tb_tipo_logradouro | co_tipo_logradouro (padrão de nome), no_tipo_logradouro (padrão de nome), no_tipo_logradouro_filtro (padrão de nome), co_tp_logradouro_cadsus (padrão de nome) |
| public.tb_tipo_material_parede | - |
| public.tb_tipo_opcao | - |
| public.tb_tipo_origem_dado_transp | - |
| public.tb_tipo_origem_energia_eletric | - |
| public.tb_tipo_paridade | - |
| public.tb_tipo_parte_bucal | - |
| public.tb_tipo_participacao_atend | - |
| public.tb_tipo_parto | - |
| public.tb_tipo_pergunta | - |
| public.tb_tipo_posse_terra | - |
| public.tb_tipo_reacao_alergia | co_seq_tipo_reacao_alergia (padrão de nome), no_tipo_reacao_alergia (padrão de nome) |
| public.tb_tipo_receita | - |
| public.tb_tipo_registro | - |
| public.tb_tipo_registro_vacinacao | - |
| public.tb_tipo_servico | - |
| public.tb_tipo_situacao_moradia | - |
| public.tb_tipo_terra | - |
| public.tb_tipo_topico_notificacao | - |
| public.tb_tipo_tratamento_agua | - |
| public.tb_tipo_unidade_saude | - |
| public.tb_titulo_patente | - |
| public.tb_topico_notificacao | - |
| public.tb_uf | - |
| public.tb_unidade_medida | - |
| public.tb_unidade_medida_tempo | - |
| public.tb_unidade_saude | nu_cnpj (padrão de nome), nu_telefone_comercial (padrão de nome), nu_telefone_comercial2 (padrão de nome), nu_telefone_fax (padrão de nome), ds_email (padrão de nome), ds_cep (padrão de nome), ds_complemento (padrão de nome), ds_logradouro (padrão de nome), co_localidade_endereco (padrão de nome), no_bairro (padrão de nome), no_bairro_filtro (padrão de nome), tp_logradouro (padrão de nome) |
| public.tb_usuario | co_seq_usuario (padrão de nome), ds_senha (padrão de nome), dt_ultima_atualizacao_senha (padrão de nome), st_forcar_troca_senha (padrão de nome), ds_login (padrão de nome), dt_envio_email_recuperar_senha (padrão de nome), dt_primeiro_login_versao (padrão de nome) |
| public.tb_vacinacao | co_prontuario (padrão de nome) |
| public.tb_via_adm_vacina | - |
| public.tb_videochamada | - |
| public.tb_vinculacao_equipes | co_equipe_principal (padrão de nome) |
| public.tb_visibilidade_lembrete | - |
| public.tb_visita_domiciliar_acs | - |
| public.tl_acesso | - |
| public.tl_ad_cidadao | co_seq_ad_cidadao (padrão de nome), co_cid10_principal (padrão de nome), co_cid10_causa_associada (padrão de nome), co_prontuario (padrão de nome), co_cid10_secundario_2 (padrão de nome), st_cidadao_sincronizado (padrão de nome), nu_documento_obito (padrão de nome), co_unico_ad_cidadao_obito (padrão de nome), co_unico_ad_cidadao (padrão de nome) |
| public.tl_ad_cidadao_historico | co_seq_ad_cidadao_historico (padrão de nome), co_unico_ad_cidadao (padrão de nome) |
| public.tl_adm_geral | - |
| public.tl_adm_municipal | - |
| public.tl_agendado | co_motivo_reserva (padrão de nome), ds_outro_motivo_reserva (padrão de nome), co_prontuario (padrão de nome), st_cidadao_agendamento_online (padrão de nome) |
| public.tl_antecedente | co_prontuario (padrão de nome), ds_alergia_medicamento (padrão de nome) |
| public.tl_antecedente_ciap | co_prontuario (padrão de nome) |
| public.tl_antecedente_historico | - |
| public.tl_antecedente_item | - |
| public.tl_aplicacao_medicamento | co_aplicacao_medicamento (padrão de nome), no_aplicacao_medicamento (padrão de nome) |
| public.tl_atend | co_prontuario (padrão de nome), dt_ultima_alteracao_status (padrão de nome) |
| public.tl_atend_proced | co_cid10_principal (padrão de nome) |
| public.tl_atend_prof | co_unico_ad_cidadao (padrão de nome) |
| public.tl_atend_prof_conduta | - |
| public.tl_atend_prof_odonto | - |
| public.tl_atend_prof_odonto_tipo_encm | - |
| public.tl_atend_prof_odonto_tipo_frnc | - |
| public.tl_atend_prof_pre_natal | - |
| public.tl_atend_prof_puericultura | - |
| public.tl_atend_prof_tipo_encam_intrn | - |
| public.tl_atend_tipo_servico | - |
| public.tl_atestado | co_seq_atestado (padrão de nome), dt_atestado (padrão de nome), ds_atestado (padrão de nome), co_prontuario (padrão de nome) |
| public.tl_ator | - |
| public.tl_ator_papel | - |
| public.tl_ator_papel_perfil | - |
| public.tl_cds_atend_dom_proced | - |
| public.tl_cds_atend_dom_situacao_pres | - |
| public.tl_cds_atend_domiciliar | dt_nascimento (padrão de nome), co_cid10 (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tl_cds_atend_individual | co_prontuario (padrão de nome), nu_prontuario (padrão de nome), dt_nascimento (padrão de nome), co_cid10 (padrão de nome), co_cid10_2 (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tl_cds_atend_individual_ciap | - |
| public.tl_cds_atend_individual_condut | - |
| public.tl_cds_atend_individual_nasf | - |
| public.tl_cds_atend_odont_tip_vig_buc | - |
| public.tl_cds_atend_odonto | dt_nascimento (padrão de nome), nu_prontuario (padrão de nome), st_gestante (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tl_cds_atend_odonto_tipo_cnslt | - |
| public.tl_cds_atend_odonto_tipo_encam | - |
| public.tl_cds_atend_odonto_tipo_fornc | - |
| public.tl_cds_ativ_col_participante | dt_nascimento (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tl_cds_aval_eleg_ad_tipo_inelg | - |
| public.tl_cds_aval_eleg_cds_situc_prs | - |
| public.tl_cds_aval_elegibilidade | co_cid10_principal (padrão de nome), co_cid10_segundo (padrão de nome), co_cid10_terceiro (padrão de nome), co_localidade_cidadao (padrão de nome), co_localidade_cidadao_nasc (padrão de nome), co_raca_cor (padrão de nome), tp_logradouro (padrão de nome), ds_complemento (padrão de nome), ds_email_cidadao (padrão de nome), dt_nascimento (padrão de nome), no_bairro (padrão de nome), no_cidadao (padrão de nome), no_logradouro (padrão de nome), no_mae_cidadao (padrão de nome), no_social_cidadao (padrão de nome), nu_cep (padrão de nome), nu_cns_cidadao (padrão de nome), nu_fone_referencia (padrão de nome), nu_fone_residencia (padrão de nome), nu_nis_pis_pasep (padrão de nome), nu_prontuario (padrão de nome), st_desconhece_nome_mae (padrão de nome), co_etnia (padrão de nome), no_pai_cidadao (padrão de nome), st_desconhece_nome_pai (padrão de nome), nu_cns_cuidador (padrão de nome), nu_cpf_cidadao (padrão de nome), nu_cpf_cuidador (padrão de nome) |
| public.tl_cds_cad_domiciliar | no_bairro (padrão de nome), nu_cep (padrão de nome), ds_complemento (padrão de nome), nu_fone_referencia (padrão de nome), nu_fone_residencia (padrão de nome), no_logradouro (padrão de nome), tp_logradouro (padrão de nome), no_logradouro_filtro (padrão de nome), no_responsavel_tecnico (padrão de nome), nu_cns_responsavel_tecnico (padrão de nome), nu_fone_responsavel_tecnico (padrão de nome), ds_complemento_filtro (padrão de nome), nu_latitude (padrão de nome), nu_longitude (padrão de nome), co_tipo_endereco (padrão de nome) |
| public.tl_cds_cad_individual | dt_nascimento_responsavel (padrão de nome), nu_cartao_sus_responsavel (padrão de nome), nu_pis_pasep (padrão de nome), st_responsavel_familiar (padrão de nome), nu_cns_cidadao (padrão de nome), no_cidadao (padrão de nome), no_social_cidadao (padrão de nome), dt_nascimento (padrão de nome), co_raca_cor (padrão de nome), no_mae_cidadao (padrão de nome), st_desconhece_nome_mae (padrão de nome), nu_celular_cidadao (padrão de nome), ds_email_cidadao (padrão de nome), no_cidadao_filtro (padrão de nome), co_etnia (padrão de nome), no_pai_cidadao (padrão de nome), st_desconhece_nome_pai (padrão de nome), nu_declaracao_obito (padrão de nome), nu_cpf_cidadao (padrão de nome), nu_cpf_responsavel (padrão de nome) |
| public.tl_cds_cidadao_resposta | co_seq_cds_cidadao_resposta (padrão de nome) |
| public.tl_cds_domicilio | tp_logradouro (padrão de nome), ds_complemento (padrão de nome), no_logradouro (padrão de nome), no_bairro (padrão de nome), ds_cep (padrão de nome), nu_fone_referencia (padrão de nome), nu_fone_residencia (padrão de nome), no_responsavel_tecnico (padrão de nome), nu_cns_responsavel_tecnico (padrão de nome), nu_contato_responsavel_tecnico (padrão de nome), nu_latitude (padrão de nome), nu_longitude (padrão de nome) |
| public.tl_cds_domicilio_familia | dt_nascimento (padrão de nome), nu_prontuario (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tl_cds_domicilio_resposta | - |
| public.tl_cds_ficha_atend_domiciliar | co_cds_prof_principal (padrão de nome) |
| public.tl_cds_ficha_atend_indivdl_prf | - |
| public.tl_cds_ficha_atend_individual | - |
| public.tl_cds_ficha_atend_odonto | - |
| public.tl_cds_ficha_atend_odonto_prof | - |
| public.tl_cds_ficha_ativ_col | co_cds_prof_responsavel (padrão de nome) |
| public.tl_cds_ficha_ativ_col_pratica | - |
| public.tl_cds_ficha_ativ_col_prof | - |
| public.tl_cds_ficha_ativ_col_pub_alvo | - |
| public.tl_cds_ficha_ativ_col_tema | - |
| public.tl_cds_ficha_consumo_alimentar | nu_cns_cidadao (padrão de nome), no_identificacao_cidadao (padrão de nome), dt_nascimento_cidadao (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tl_cds_ficha_proced | - |
| public.tl_cds_ficha_vacinacao | - |
| public.tl_cds_ficha_visita_domiciliar | - |
| public.tl_cds_proced | dt_nascimento (padrão de nome), nu_prontuario (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tl_cds_prof | nu_cns (padrão de nome) |
| public.tl_cds_vacina | co_cid10_motivo_indicacao (padrão de nome) |
| public.tl_cds_vacinacao | nu_prontuario (padrão de nome), dt_nascimento (padrão de nome), st_gestante (padrão de nome), nu_cpf_cidadao (padrão de nome) |
| public.tl_cds_visita_domiciliar | dt_nascimento (padrão de nome), nu_prontuario (padrão de nome), nu_cpf_cidadao (padrão de nome), nu_latitude (padrão de nome), nu_longitude (padrão de nome) |
| public.tl_cidadao | co_unico_cidadao_prontuario (padrão de nome), co_unico_prontuario (padrão de nome), co_seq_cidadao (padrão de nome), st_desconhece_nome_mae (padrão de nome), st_nao_possui_cns (padrão de nome), nu_nis_pis_pasep (padrão de nome), nu_cns_responsavel (padrão de nome), no_responsavel (padrão de nome), dt_nascimento_responsavel (padrão de nome), nu_cns_cuidador (padrão de nome), no_cuidador (padrão de nome), dt_nascimento_cuidador (padrão de nome), co_unico_cidadao (padrão de nome), co_pais_nascimento (padrão de nome), st_desconhece_nome_pai (padrão de nome), st_infrm_orientacao_sexual (padrão de nome), tp_orientacao_sexual (padrão de nome), st_infrm_identidade_genero (padrão de nome), tp_identidade_genero (padrão de nome), st_compartilhamento_prontuario (padrão de nome), dt_ultima_alteracao_cns (padrão de nome), nu_cpf (padrão de nome), nu_cns (padrão de nome), no_cidadao (padrão de nome), no_cidadao_filtro (padrão de nome), co_raca_cor (padrão de nome), co_etnia (padrão de nome), dt_nascimento (padrão de nome), no_mae (padrão de nome), no_mae_filtro (padrão de nome), no_pai (padrão de nome), no_social (padrão de nome), nu_documento_obito (padrão de nome), ds_cep (padrão de nome), ds_complemento (padrão de nome), ds_logradouro (padrão de nome), co_localidade_endereco (padrão de nome), no_bairro (padrão de nome), no_bairro_filtro (padrão de nome), tp_logradouro (padrão de nome), nu_telefone_residencial (padrão de nome), nu_telefone_celular (padrão de nome), nu_telefone_contato (padrão de nome), ds_email (padrão de nome), st_territorio_utiliza_cpf (padrão de nome), nu_cpf_cuidador (padrão de nome), nu_cpf_responsavel (padrão de nome), no_tipo_sanguineo (padrão de nome), no_sexo (padrão de nome) |
| public.tl_cidadao_grupo | co_seq_cidadao_grupo (padrão de nome), nu_cns (padrão de nome), co_cidadao (padrão de nome), co_cidadao_master (padrão de nome), co_cidadao_unificado (padrão de nome), nu_cpf (padrão de nome) |
| public.tl_cidadao_nucleo_familiar | co_seq_cidadao_nucleo_familiar (padrão de nome), nu_cpf_cns_responsavel (padrão de nome), st_responsavel (padrão de nome), co_cidadao (padrão de nome), nu_cns_profissional (padrão de nome) |
| public.tl_cidadao_vinculacao_equipe | co_seq_cidadao_vinculacao_eqp (padrão de nome), co_cidadao (padrão de nome) |
| public.tl_cns | co_seq_cns (padrão de nome), nu_cns (padrão de nome), co_cidadao (padrão de nome) |
| public.tl_config_agenda_detalhe | - |
| public.tl_config_atencao_domiciliar | qt_tempo_duracao_consulta (padrão de nome) |
| public.tl_configperiodo_diasemana | - |
| public.tl_configuracao_horario | tempo_duracao_consulta (padrão de nome) |
| public.tl_encaminhamento | co_prontuario (padrão de nome), ds_complemento (padrão de nome), co_cid10 (padrão de nome) |
| public.tl_equipe | - |
| public.tl_evol_aval_tp_vig_saude_bucl | - |
| public.tl_evolucao_avaliacao | - |
| public.tl_evolucao_avaliacao_ciap_cid | co_seq_evolucao_aval_ciap_cid (padrão de nome), co_cid10 (padrão de nome) |
| public.tl_evolucao_dente | - |
| public.tl_evolucao_objetivo | - |
| public.tl_evolucao_odonto | co_prontuario (padrão de nome) |
| public.tl_evolucao_odonto_parte_bucal | - |
| public.tl_evolucao_odonto_proced | - |
| public.tl_evolucao_plano | - |
| public.tl_evolucao_plano_ciap | - |
| public.tl_evolucao_subjetivo | - |
| public.tl_evolucao_subjetivo_ciap | - |
| public.tl_exame_clearance_creatina | - |
| public.tl_exame_colesterol_hdl | - |
| public.tl_exame_colesterol_ldl | - |
| public.tl_exame_colesterol_total | - |
| public.tl_exame_creatina_serica | - |
| public.tl_exame_hemoglobina_glicada | - |
| public.tl_exame_prenatal | - |
| public.tl_exame_puericultura | - |
| public.tl_exame_requisitado | co_prontuario (padrão de nome) |
| public.tl_exame_triglicerideos | - |
| public.tl_familia | nu_cpf_cns_responsavel (padrão de nome), nu_prontuario_familiar (padrão de nome), dt_nascimento_responsavel (padrão de nome), st_responsavel_cadastrado (padrão de nome), st_responsavel_declarado (padrão de nome), st_responsavel_vivo (padrão de nome), st_responsavel_unico (padrão de nome), st_responsavel_ainda_reside (padrão de nome) |
| public.tl_grupo_ativ_col | - |
| public.tl_imunobiologico_lote | - |
| public.tl_justificativa_prontuario | dt_acesso_prontuario (padrão de nome), co_prontuario (padrão de nome), co_usuario (padrão de nome) |
| public.tl_lembrete | dt_prontuario_lembrete (padrão de nome), co_prontuario (padrão de nome) |
| public.tl_lembrete_evolucao | dt_prontuario_lembrete (padrão de nome) |
| public.tl_lotacao | - |
| public.tl_medicamento | co_seq_medicamento (padrão de nome), ds_concentracao (padrão de nome) |
| public.tl_medicamento_uso_continuo | co_medicamento (padrão de nome), co_prontuario (padrão de nome), co_ultima_receita_medicamento (padrão de nome) |
| public.tl_medicao | nu_medicao_saturacao_o2 (padrão de nome) |
| public.tl_neuro_alter_fenot | co_prontuario (padrão de nome) |
| public.tl_neuro_alter_fenot_evolucao | - |
| public.tl_neuro_fator_risco | co_prontuario (padrão de nome) |
| public.tl_neuro_fator_risco_evolucao | - |
| public.tl_neuro_marco | co_prontuario (padrão de nome) |
| public.tl_neuro_marco_evolucao | - |
| public.tl_odontograma | co_prontuario (padrão de nome) |
| public.tl_orientacao | co_prontuario (padrão de nome) |
| public.tl_papel | - |
| public.tl_perfil | - |
| public.tl_pre_natal | co_prontuario (padrão de nome) |
| public.tl_problema | co_cid10 (padrão de nome), co_prontuario (padrão de nome) |
| public.tl_problema_evolucao | - |
| public.tl_proced_cds_proced | - |
| public.tl_prof | nu_cpf (padrão de nome), nu_cns (padrão de nome), no_profissional_filtro (padrão de nome), dt_nascimento (padrão de nome), nu_telefone (padrão de nome), ds_email (padrão de nome), ds_cep (padrão de nome), ds_complemento (padrão de nome), ds_logradouro (padrão de nome), co_localidade_endereco (padrão de nome), no_bairro (padrão de nome), no_bairro_filtro (padrão de nome), tp_logradouro (padrão de nome) |
| public.tl_prof_municipio | - |
| public.tl_prontuario | co_seq_prontuario (padrão de nome), co_unico_prontuario (padrão de nome), co_unico_cidadao_prontuario (padrão de nome), co_prontuario_grupo (padrão de nome), co_cidadao (padrão de nome), st_cidadao_processado (padrão de nome) |
| public.tl_prontuario_grupo_historico | co_seq_prontuario_grpo_hstrco (padrão de nome), co_prontuario_grupo (padrão de nome), co_prontuario (padrão de nome) |
| public.tl_qst_opcao_pergunta | - |
| public.tl_qst_questionario_respondido | - |
| public.tl_qst_resposta | - |
| public.tl_qst_resposta_opcao_pergunta | - |
| public.tl_receita | - |
| public.tl_receita_medicamento | co_seq_receita_medicamento (padrão de nome), co_aplicacao_medicamento (padrão de nome), co_medicamento (padrão de nome), qt_duracao_tratamento (padrão de nome) |
| public.tl_recurso | - |
| public.tl_registro_vacinacao | - |
| public.tl_requisicao_exame | co_cid10 (padrão de nome) |
| public.tl_rl_cds_visita_dom_motivo | - |
| public.tl_sinan_notificacao_evolucao | co_prontuario (padrão de nome) |
| public.tl_unidade_saude | nu_cnpj (padrão de nome), nu_telefone_comercial (padrão de nome), nu_telefone_comercial2 (padrão de nome), nu_telefone_fax (padrão de nome), ds_email (padrão de nome), ds_cep (padrão de nome), ds_complemento (padrão de nome), ds_logradouro (padrão de nome), no_bairro (padrão de nome), no_bairro_filtro (padrão de nome), tp_logradouro (padrão de nome) |
| public.tl_unidade_saude_complexidade | - |
| public.tl_unidade_saude_tipo_servico | - |
| public.tl_usuario | co_seq_usuario (padrão de nome), ds_senha (padrão de nome), st_trocar_senha (padrão de nome), dt_ultima_atualizacao_senha (padrão de nome), st_forcar_troca_senha (padrão de nome) |
| public.tl_vacinacao | st_gestante (padrão de nome), co_prontuario (padrão de nome) |


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

Total de colunas com PII de conteúdo detectada: **7**

| Tabela | Colunas com PII embutida |
|--------|---------------------------|
| public.ta_orientacao | ds_orientacao |
| public.tb_dim_cidadao_pec_grupo | co_identificacao |
| public.tb_dim_profissional | ds_filtro |
| public.tb_envio_rnds | ds_erro |
| public.tb_orientacao | ds_orientacao |
| public.tb_recebimento_validacao_erros | ds_erro_campo_invalido |
| public.tl_imunobiologico_lote | ds_lote |


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
