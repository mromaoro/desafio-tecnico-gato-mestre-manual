# Respostas Oficiais às Questões do Desafio Técnico

**Gato Mestre | Previsão de Pontuação de Atletas (Cartola FC)**  
*Candidato: Matheus Romão*  
*Documento de Síntese Metodológica e Respostas Formais*

---

## Questão 1: Que inconsistências você encontrou na base? Para cada uma, qual foi o tratamento adotado e por quê?

Durante o diagnóstico exploratório da base bruta (`base_case_gm.csv`, contendo 117.469 registros) e o cruzamento com os endpoints da API oficial de apoio, foram identificadas e tratadas **7 inconsistências estruturais**, adotando a API como fonte canônica da verdade (*Single Source of Truth*):

### 1. Inconsistência de Cardinalidade em `posicao_id`
* **Inconsistência Identificada:** Foram encontradas 466 linhas com valores espúrios de posição (`0`, `7` e `9`), em desacordo com as 6 posições regulamentares do Cartola FC (1 a 6), além de divergências de posição atribuídas ao mesmo atleta ao longo das temporadas.
* **Tratamento Adotado (Tratamento 1):** Mapeamento direto a partir do cadastro oficial da API (`api_atletas.json` via `GET /atletas`), sobrescrevendo 100% dos atletas com sua `posicao_id` regulamentar canônica.
* **Justificativa:** A API de atletas representa o cadastro mestre oficial; a correção cadastral elimina o ruído sem necessidade de descartar amostras.

### 2. Dados Faltantes de Contexto (`home_dummy` e `opponent`) e IDs Fictícios
* **Inconsistência Identificada:** A base bruta continha 14.082 valores nulos em `home_dummy` (11,99%), 13.995 nulos em `opponent` (11,91%) e 702 registros com identificadores de oponentes fictícios (`777`, `888`, `999`).
* **Tratamento Adotado (Tratamento 2):** Como o `match_id` estava preservado, realizou-se o cruzamento com `api_jogos.json` (`GET /jogos`), recalculando o mando de campo exato (`home_dummy = 1` se `clube_id == equipe_mandante_id`) e recuperando o ID real do adversário.
* **Justificativa:** O mando de campo e a força defensiva/ofensiva do adversário são variáveis contextuais fundamentais para modelar o potencial de pontuação em esportes coletivos.

### 3. Coluna 100% Nula (`DD`) e Saneamento de `preco_num`
* **Inconsistência Identificada:**
  * Coluna `DD` (Defesa Difícil): 100% nula (117.469 ausências), em função da unificação das regras do Cartola FC, que consolidou defesas de goleiro no scout geral `DE`.
  * Coluna `preco_num`: 3.493 linhas com separador decimal em vírgula (`'1,0'`), 942 preços negativos (sinal negativo espúrio) e 20 valores nulos reais.
* **Tratamento Adotado (Tratamento 3):**
  * Exclusão definitiva da coluna `DD`.
  * Conversão de vírgulas para pontos, aplicação de `abs()` para assegurar preços estritamente positivos e imputação dos 20 nulos pela série temporal do atleta ($t-1 / t+1$) ou mediana da posição.
* **Justificativa:** Colunas com variância zero não agregam sinal em árvores e geram singularidade matricial ($X^T X$) em modelos lineares; preços negativos violam a regra de mercado do fantasy ($P > 0$).

### 4. Duplicidades Estritas e Conflitos na Mesma Partida (`match_id`)
* **Inconsistência Identificada:** 1.163 pares de linhas 100% idênticas em todas as 38 colunas (2.326 registros redundantes / 1,98% da base) e 1.386 linhas com duplicidade na chave `atleta_id + match_id` apresentando dados conflitantes (uma linha completa com scouts reais e outra incompleta/zerada).
* **Tratamento Adotado (Tratamento 4):** Deduplicação estrita via `drop_duplicates()` e consulta às súmulas oficiais em `api_jogos_detalhes.json` (`GET /jogos/{jogo_id}`) para preservar a linha com a atuação real em campo.
* **Justificativa:** Elimina a distorção de pesos amostrais e previne a contaminação do treinamento com registros incompletos.

### 5. Inconsistência de Domínio em `rodada_id` (Valores 0, 39, 41 e 99)
* **Inconsistência Identificada:** 587 registros continham valores de rodada fora do calendário oficial de 38 rodadas do Brasileirão (`rodada_id = 0` (155), `39` (135), `41` (155) e `99` (142)), gerando distorções em agrupamentos temporais.
* **Tratamento Adotado (Tratamento 5):** Mapeamento da rodada regulamentar oficial (1 a 38) de cada partida a partir de `api_jogos.json`.
* **Justificativa:** Garante alinhamento cronológico correto para a criação de janelas móveis defasadas (*lags*).

### 6. Anomalias em `minutos_jogados` e Discrepâncias de Participação
* **Inconsistência Identificada:** 10.426 valores nulos em `minutos_jogados` (8,88%), 1.873 valores anômalos (3 minutos negativos e 1.870 minutos excessivos $> 105\text{ min}$, chegando a $1.440\text{ min}$ por erro de escala) e 1.207 casos com `entrou_em_campo == False` mas minutos $> 0$.
* **Tratamento Adotado (Tratamento 6):** Reconstituição da minutagem canônica a partir dos eventos de substituição de `api_jogos_detalhes.json` (Titular $= 90\text{ min}$, titular substituído $= X\text{ min}$, reserva que entrou $= 90-Y\text{ min}$, não atuou $= 0.0\text{ min}$).
* **Justificativa:** A minutagem precisa é indispensável para calcular métricas de intensidade (taxa de scouts por 90 minutos) e volume de jogo.

### 7. Padronização Textual de Variáveis Categóricas
* **Inconsistência Identificada:** Registros de `status_inicial` com valor numérico `'0'`; variações textuais e espaços em `status_pre` (`' Nulo '`, `'PROVÁVEL'`); `apelido` em caixa alta ou formatos irregulares (`'DIEGO HOLLANDA 2'`).
* **Tratamento Adotado (Tratamento 7):** Sincronização de `status_inicial` com as súmulas (`'titular'` e `'reserva'`), padronização de `status_pre` em categorias limpas (`'Provável'`, `'Dúvida'`, `'Contundido'`, `'Suspenso'`, `'Nulo'`) e `apelido` canônico em Title Case via API.
* **Justificativa:** Evita a fragmentação de categorias em nós de árvores e melhora a qualidade dos dados em produção.

---

## Questão 2: Como você dividiu os dados entre treino e validação? Justifique tecnicamente o critério escolhido.

### 1. Estrutura da Divisão Temporal (*Out-of-Time Validation*)
A divisão foi estruturada de forma estritamente cronológica por temporadas inteiras, abrangendo **todos os 115.613 atletas cadastrados** (sem viés de sobrevivência ou filtros de exclusão):

```
┌──────────────────────────────────────┬────────────────────────┬────────────────────────┐
│      Treino (Safras 2022 e 2023)     │ Validação (Safra 2024) │ Teste OOS (Safra 2025) │
│            59.213 registros          │    28.568 registros    │    27.832 registros    │
│       Calibragem dos Modelos         │   Tuning de Hiperpar.  │   Avaliação Cega Final │
└──────────────────────────────────────┴────────────────────────┴────────────────────────┘
```

* **Treino ($N = 59.213$):** Safras 2022 e 2023 completas, utilizadas para o treinamento dos baselines lineares e dos modelos de árvores/ensembles.
* **Validação ($N = 28.568$):** Safra 2024 completa, utilizada para a seleção de modelos e otimização Bayesiana de hiperparâmetros (*Optuna / TPE*).
* **Teste / Out-of-Sample OOS ($N = 27.832$):** Safra 2025 completa, mantida estritamente isolada durante toda a modelagem para avaliação cega de generalização e geração do arquivo oficial `previsoes.json`.

### 2. Justificativa Técnica
1. **Prevenção Rigorosa a *Lookahead Bias* (Vazamento Temporal):** Em dados esportivos e de mercado, o uso de *K-Fold Cross-Validation* aleatório é inadequado porque permite que dados do futuro treinem o modelo para prever o passado. Isso infla artificialmente métricas de acurácia que não se sustentam em produção.
2. **Mimetização Fiel do Ciclo Produtivo:** No Cartola FC, o modelo precisa estimar o desempenho de rodadas futuras em temporadas com novos elencos, transferências internacionais, alterações táticas e trocas de técnicos. A validação *Out-of-Time* por ano garante que o modelo aprendeu padrões estruturais generalizáveis e não correlações espúrias intra-safra.

---

## Questão 3: Quais colunas da base você utilizou como variáveis do modelo, e quais deixou de fora? Explique os dois lados da decisão.

A base bruta e enriquecida totalizou 70 colunas. A seleção final utilizou **37 variáveis preditoras pré-jogo (`feature_cols_all`)**, guiada pela **Regra de Ouro da Modelagem Preditiva**: *Zero Data Leakage*.

### 1. O Lado das Colunas Deixadas de Fora (Descarte e Isolamento)

* **Variável Alvo (*Target*):** `pontos_num` foi estritamente isolada como a variável de desfecho $y$.
* **Identificadores e Metadados Textuais:** `atleta_id`, `match_id`, `ano`, `apelido`, `posicao_nome` foram excluídos da matriz de features preditoras (mantidos apenas como metadados para rastreabilidade e indexação).
* **Variáveis Pós-Jogo Apuradas Durante/Após a Partida ($t$):**
  * `minutos_jogados`, `entrou_em_campo`, `status_inicial` (da partida $t$).
  * `variacao_num` (variação de patrimônio pós-rodada).
  * **Todos os 19 scouts diretos da rodada $t$:** Gols (`G`), Assistências (`A`), Saldo de Gol (`SG`), Defesas (`DE`), Desarmes (`DS`), Faltas Sofridas (`FS`), Finalizações Fora (`FF`), Finalizações Defendidas (`FD`), Finalizações na Trave (`FT`), Cartões Amarelos (`CA`), Cartões Vermelhos (`CV`), Faltas Cometidas (`FC`), Gols Contra (`GC`), Gols Sofridos (`GS`), Impedimentos (`I`), Pênaltis Perdidos (`PP`), Pênaltis Cometidos (`PC`).
  * *Justificativa:* Todos esses dados só são conhecidos após o término do jogo. Utilizá-los diretamente em $t$ configuraria vazamento de dados grave (*target leakage*), inviabilizando o uso do modelo antes do fechamento do mercado.

### 2. O Lado das Colunas Utilizadas (Engenharia de Features Pré-Jogo)

Para capturar o momento e a capacidade do atleta sem gerar vazamento, os dados históricos foram transformados em **features defasadas (*lagged*) e janelas móveis**:

| Grupo de Features | Variáveis Criadas | Racional e Significado de Negócio |
| :--- | :--- | :--- |
| **Forma Recente e Regularidade Defasada** | `pontos_lag1`, `participou_lag1`, `media_pontos_3j`, `desvio_pontos_3j`, `taxa_participacao_3j`, `minutos_medios_3j`, `media_scouts_volume_3j` | Capturam a fase recente, regularidade e frequência de atuação do atleta nas últimas 3 partidas. |
| **Scouts Especializados Defasados** | `media_desarmes_3j`, `media_finalizacoes_3j`, `taxa_participacao_gols_5j`, `taxa_defesas_por_jogo_3j`, `taxa_conversao_gols_5j`, `score_risco_disciplinar_5j` | Isola o volume de ações decisivas e disciplinares por posição em janelas de 3 e 5 jogos. |
| **Contexto de Confronto e Força Coletiva** | `diff_forca_confronto`, `fator_alavancagem_confronto`, `potencial_esperado_atleta`, `indice_favoritismo_mando`, `volume_esperado_partida`, `expectativa_gols_time`, `potencial_sg_defesa`, `home_dummy` | Modula a média do atleta contra a fragilidade defensiva do adversário e o favoritismo do mando de campo. |
| **Dinâmica Econômica e Tática** | `preco_mercado_pre`, `momentum_preco_3j`, `roi_recente_3j`, `diff_preco_posicao_pre`, `score_risco_rotacao`, `estabilidade_11_titular_clube`, `status_pre`, `status_inicial`, `is_inicio_temporada`, `progresso_campeonato` | Incorpora o valor de mercado (precificação implícita do ecossistema), momento de valorização e risco de rotatividade tática. |

---

## Questão 4: Que métricas você usou para avaliar o modelo, e por quê? O resultado obtido justifica colocar a solução em uso?

### 1. Métricas Utilizadas e Resultados na Safra de Teste Out-of-Sample (Safra 2025 - $N = 27.832$)

Para avaliar tanto a **precisão numérica** quanto a **utilidade prática para escalação (ranqueamento)**, foram empregadas 5 métricas complementares:

| Modelo | MAE (pts) | RMSE (pts) | $R^2$ (Var. Explicada) | Spearman $\rho$ (Ranking) | Kendall $\tau$ (Pares) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Baseline Heurístico (Média Histórica)** | $2.3160$ | $3.2798$ | $-0.0001$ | $0.2310$ | $0.1740$ |
| **Regressão Linear (OLS)** | $1.7240$ | $2.4110$ | $0.1850$ | $0.4820$ | $0.3650$ |
| **Random Forest** | $1.4420$ | $2.1480$ | $0.3280$ | $0.5870$ | $0.4510$ |
| **CatBoost Regressor** | $1.4215$ | $2.1280$ | $0.3390$ | $0.5940$ | $0.4570$ |
| 🏆 **LightGBM Tunado (Campeão)** | **$1.4103$** | **$2.1152$** | **$0.3451$** | **$0.6011$** | **$0.4633$** |

#### Justificativa das Métricas:
* **MAE ($1.4103\text{ pts}$):** Mede o erro médio absoluto na mesma escala do jogo. Reduziu o erro do baseline em quase $1.0\text{ ponto}$ por atleta.
* **RMSE ($2.1152\text{ pts}$):** Penaliza severamente erros em casos extremos (goleadas ou expulsões inesperadas).
* **$R^2$ ($0.3451$):** Demonstra que o modelo explica mais de $34,5\%$ de toda a variância de pontuação em uma base completa com 27.832 atletas (incluindo reservas e nulos).
* **Spearman $\rho$ ($0.6011$) e Kendall $\tau$ ($0.4633$):** Métricas centrais de negócio para fantasy game. Comprovam que a ordenação relativa dos atletas tem forte concordância com a realidade em campo.

---

### 2. O resultado obtido justifica colocar a solução em uso?

**Sim, a solução sustenta o uso em produção, desde que acompanhada do desenho de produto adequado.**

#### Racional de Sustentação de Negócio:
1. **Superação Estrutural dos Indicadores Atuais:** A informação hoje disponível ao usuário no Cartola FC é puramente descritiva (`media_num`, preço e últimos jogos). O modelo campeão supera o baseline em todas as dimensões, ajustando a expectativa pelo mando de campo, força do adversário e momento tático.
2. **Alta Capacidade de Ranqueamento ($\rho = 0.6011$):** Para o usuário que está escalando, o mais importante não é prever com precisão decimal se um atleta fará $5.8$ ou $6.2\text{ pts}$, mas sim saber **se o Atleta A tem maior expectativa de pontuação que o Atleta B** naquela rodada específica.

#### Recomendações de Engenharia e Design de Produto:
* **Exposição com Faixas de Potencial / Incerteza:** O futebol possui volatilidade intrínseca inerente a eventos estocásticos raros (pênaltis, expulsões aos 5 minutos, falhas individuais). Exibir uma previsão pontual determinística única (ex: *"Gabriel fará 6.04 pts"*) pode gerar falsa sensação de certeza e frustração no usuário. Recomenda-se apresentar a pontuação acompanhada de uma **faixa de potencial** (ex: *"Expectativa: 6.0 pts [Faixa provável: 3.5 a 8.5 pts]"*) ou de um **Score de Potencial Gato Mestre**.
* **Evolução Arquitetural no Roadmap:** Para iterações futuras, recomenda-se explorar arquiteturas em dois estágios (*Two-Stage / Hurdle Model* com classificador de probabilidade de atuação $P(\text{joga})$ desacoplado do regressor de potencial condicional $E[Y \mid \text{joga}]$) e modelos de regressão quantílica para estimar diretamente os percentis $P_{10}$ e $P_{90}$.

---

### 3. Estratégia de MLOps & Monitoramento Contínuo em Produção

Para sustentar a confiabilidade do modelo ao longo das 38 rodadas do Brasileirão, propõe-se uma esteira de observabilidade pós-rodada focada na detecção dos três tipos de *drift*:

1. **Data Drift (Covariate Shift - $P(X)$):**
   * *Gatilho no Negócio:* Janelas de transferências internacionais (entrada massiva de atletas sem histórico) e mudanças de critérios disciplinares da arbitragem.
   * *Métrica e Alerta:* Testes Kolmogorov-Smirnov (KS) em variáveis contínuas (`media_pontos_3j`, `diff_forca_confronto`) e Population Stability Index ($\text{PSI} > 0.20$).
2. **Target Drift (Prior Shift - $P(Y)$):**
   * *Gatilho no Negócio:* Mudança estrutural na média de gols do campeonato ou alterações nas pontuações de scouts pela organização do Cartola.
   * *Métrica e Alerta:* Distância de Wasserstein e monitoramento da média móvel de `pontos_num` por rodada.
3. **Concept / Model Drift ($P(Y \mid X)$):**
   * *Gatilho no Negócio:* Quebra de relações funcionais históricas (ex: clube tradicional que entra em crise técnica e perde a vantagem histórica de mando de campo).
   * *Métrica e Gatilho de Retreino:* Acompanhamento contínuo do MAE e do Spearman $\rho$ pós-rodada. Se o erro da rodada exceder $1.85\text{ pts}$ (+30% vs benchmark) ou o Spearman cair abaixo de $0.40$, aciona-se o pipeline de retreino automatizado (*Rolling Retraining*) com os dados mais recentes.
