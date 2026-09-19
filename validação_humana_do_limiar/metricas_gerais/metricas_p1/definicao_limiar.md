# Análise Técnica do Limiar de Similaridade Semântica

Este documento apresenta a análise detalhada para a definição do limiar (threshold) de similaridade semântica, integrando a **validação humana** e a **análise de sensibilidade automatizada** (estudo de platô).

## 1. Metodologia de Análise

Para definir o limiar ideal, cruzamos duas abordagens distintas:

1.  **Abordagem Automatizada (Estudo de Platô)**: Análise da estabilidade do coeficiente SoftDice em função do limiar em cada base (`step4_output/sensitivity`). O "platô" é a região onde a métrica de consistência permanece estável antes de sofrer uma queda abrupta.
2.  **Abordagem de Validação Humana**: Comparação de predições do algoritmo contra rótulos de especialistas humanos, utilizando a métrica F1-Score para encontrar o ponto de equilíbrio entre Precisão e Recall.

---

## 2. Análise por Base de Dados

### 2.1. Magento2
- **Platô Automatizado**: Estabilidade observada entre **$0.0$ e $0.35$**. A partir de $0.35$, a similaridade média começa a cair.
- **Validação Humana**: O F1-Score cresce consistentemente até atingir seu pico em **$0.45$ - $0.49$** ($\text{F1} \approx 0.83$).
- **Observação**: O limiar humano ótimo está acima do platô automatizado, indicando que para evitar falsos positivos nesta base, é necessário um rigor maior do que a simples estabilidade da média.

### 2.2. Nhanes
- **Platô Automatizado**: Estabilidade observada entre **$0.0$ e $0.25$**.
- **Validação Humana**: Apresentou a maior concordância de todas as bases, com pico de performance em **$0.49$** ($\text{F1} = 0.93$).
- **Observação**: Existe um gap significativo entre o fim do platô automatizado ($0.25$) e o ótimo humano ($0.49$), evidenciando que a similaridade semântica bruta sozinha (SoftDice) subestima o ponto de corte necessário para a equivalência real.

### 2.3. Teixeira
- **Platô Automatizado**: Estabilidade observada entre **$0.0$ e $0.30$**.
- **Validação Humana**: O pico de performance ocorre em **$0.48$ - $0.49$** ($\text{F1} \approx 0.83$).
- **Observação**: Assim como nas outras bases, o limiar humano ótimo situa-se consistentemente acima da região de estabilidade automatizada.

---

## 3. Análise Agregada e Conclusão

Ao agregar as três bases, observamos o seguinte comportamento:

| Métrica | Valor no Limiar $0.5$ | Comportamento |
| :--- | :---: | :--- |
| **F1-Score** | **$0.860$** | Pico de performance global. |
| **Acurácia** | $0.840$ | Alta concordância geral. |
| **Precision** | $0.845$ | Baixa taxa de falsos positivos. |
| **Recall** | $0.875$ | Alta capacidade de detecção de matches. |

### Justificativa Final para a Escolha do Limiar

O limiar escolhido para o pipeline é **$0.5$**.

**Justificativa:**
1.  **Superação do Platô**: Embora a análise automatizada (`step4_output`) sugira estabilidade em valores baixos ($0.25$ a $0.35$), a validação humana prova que esses valores são insuficientes para garantir a equivalência semântica, gerando excesso de falsos positivos.
2.  **Consistência Inter-Bases**: O valor de $\approx 0.5$ foi o ponto de convergência para o pico de F1-Score em todas as três bases testadas, independentemente do domínio dos dados.
3.  **Equilíbrio Ótimo**: Em $0.5$, o algoritmo atinge o melhor compromisso entre a precisão (não agrupar temas diferentes) e o recall (não ignorar temas iguais), resultando em um F1-Score global de $0.86$.

Dessa forma, a definição do limiar baseou-se na **primazia da validação humana sobre a métrica automatizada**, utilizando o estudo de platô como referência de base, mas ajustando o valor para cima para garantir a precisão semântica exigida pelo domínio.
