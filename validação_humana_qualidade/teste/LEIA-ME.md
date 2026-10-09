# Validação humana: consistência x qualidade dos temas

## Instalação
    pip install streamlit pandas numpy scipy krippendorff

## Ordem de execução (na pasta validação_humana_qualidade\teste)
1. Os Dice vêm de data\{base}\step4_output\semantic_pair_audit.json (já calculados no artigo).
2. `python 01_montar_pools.py --n 30 --piloto 4 --seed 42`
   -> manifesto, tarefas (sem origem dos temas), origens.json e mapeamento_sistemas.json (NÃO compartilhar).
3. Piloto: cada avaliador roda `streamlit run 02_interface_avaliacao.py`; as 4 primeiras tabelas de cada
   base são piloto. Calcule o alpha preliminar, ajuste o guia e só então libere a coleta.
   Distribua ao avaliador apenas: teste\ (sem origens.json/mapeamento) e data\tarefas + data\amostra\manifesto_amostra.csv
   (o manifesto contém Dice: gere uma cópia só com item_id e piloto para o avaliador).
4. `python 03_consolidar_metricas.py` -> data\consolidado\

## Regras do protocolo
- Dice: lidos de data\{base}\step4_output\semantic_pair_audit.json (nada é recalculado; não há mais 00_calcular_dice_soft.py).
- Etapa 0 (resposta livre) antes de ver qualquer tema; Etapa 1 julga temas sem origem nem contagem;
  Etapa 2 mostra listas por sistema anônimo (A/B/C) com as 3 runs; Etapa 3 mede coesão da tabela.
- Quem desenvolveu o pipeline não avalia. Avaliadores não veem Dice nem nome do modelo.
- Cada avaliador grava em data\avaliacoes\avaliacao_{id}.jsonl (evita conflito no OneDrive).
