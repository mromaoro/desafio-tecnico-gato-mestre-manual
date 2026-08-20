# Respostas Oficiais às Questões do Desafio Técnico

**Gato Mestre | Previsão de Pontuação de Atletas (Cartola FC)**  
*Candidato: Matheus Romão*  
*Documento de Síntese Metodológica e Respostas Formais*

---

## Questão 1: Que inconsistências você encontrou na base? Para cada uma, qual foi o tratamento adotado e por quê?

Durante o diagnóstico exploratório da base bruta (`base_case_gm.csv`, contendo 117.469 registros) e o cruzamento com os endpoints da API oficial de apoio, foram identificadas e tratadas **8 inconsistências estruturais**, adotando a API como fonte canônica da verdade (*Single Source of Truth*):

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

### 8. Mudança Histórica nas Regras de Pontuação dos Scouts (Concept Drift no Target)
* **Inconsistência Identificada:** As regras e pesos de pontuação dos scouts no Cartola FC variaram entre as temporadas de 2022 a 2025 (ex: pontuação de desarmes `DS`, defesas `DE`, faltas `FC`, etc.), gerando uma inconsistência de escala no target histórico original (`pontos_num`).
* **Tratamento Adotado (Tratamento 8):** Auditoria reversa determinística das regras de scouts e recálculo homogeneizado da pontuação de todos os anos retroativamente com base nos pesos oficiais de 2025 (`pontos_target_2025`), além da atribuição determinística da média dos atletas de linha do clube para os técnicos (`posicao_id == 6`).
* **Justificativa:** Elimina o viés de *Concept Drift* na variável alvo, garantindo que os modelos aprendam correlações sobre uma regra unificada e perfeitamente aderente à safra de avaliação.

---

## Questão 2: Como você dividiu os dados entre treino e validação? Justifique tecnicamente o critério escolhido.

### 1. Estrutura da Divisão Temporal (*Out-of-Time Validation*)
A divisão foi estruturada de forma estritamente cronológica por temporadas inteiras, abrangendo **todos os 115.613 atletas cadastrados**:

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
2. **Mimetização Fiel do Ciclo Produtivo:** No Cartola FC, o modelo precisa estimar o desempenho de rodadas futuras em temporadas com novos elencos, transferências internacionais, alterações táticas e trocas de técnicos. A validação *Out-of-Time* por ano garante que o modelo aprendeu padrões estruturais generalizáveis.

---

## Questão 3: Quais colunas da base você utilizou como variáveis do modelo, e quais deixou de fora? Explique os dois lados da decisão.

A base bruta e enriquecida totalizou 69 colunas. A seleção final utilizou **33 variáveis preditoras pré-jogo (`cols_to_predict`)**, estruturadas sob o princípio fundamental de **Zero Data Leakage** e agrupadas por relevância tática e esportiva.

### 1. O Lado das Colunas Deixadas de Fora (Descarte, Isolamento e Colinearidade)

* **Variável Alvo (*Target*):** `pontos_target_2025` (e o `pontos_num` bruto) foi estritamente isolada como a variável dependente de desfecho $y$.
* **Identificadores e Metadados:** `atleta_id`, `match_id`, `ano`, `rodada_id`, `clube_id`, `opponent`, `apelido`, `posicao_nome` e `rodada_cbf_original` foram excluídos da matriz preditiva $X$ (mantidos apenas como metadados de indexação e rastreabilidade).
* **Variáveis Pós-Jogo da Partida $t$ (Prevenção de *Target Leakage*):**
  * `minutos_jogados` e `entrou_em_campo` da rodada $t$ (apurados somente após a realização do jogo).
  * `preco_num`, `variacao_num`, `media_num` e `jogos_num` em sua versão original não defasada (pois refletem a consolidação pós-jogo da rodada $t$).
  * **Todos os 19 scouts diretos da rodada $t$:** Gols (`G`), Assistências (`A`), Saldo de Gol (`SG`), Defesas (`DE`), Desarmes (`DS`), Faltas Sofridas (`FS`), Finalizações Fora (`FF`), Finalizações Defendidas (`FD`), Finalizações na Trave (`FT`), Pênaltis Defendidos (`DP`), Pênaltis Sofridos (`PS`), Pênaltis Perdidos (`PP`), Pênaltis Cometidos (`PC`), Cartões Amarelos (`CA`), Cartões Vermelhos (`CV`), Faltas Cometidas (`FC`), Gols Sofridos (`GS`), Gols Contra (`GC`) e Impedimentos (`I`).
  * *Justificativa:* Utilizar scouts ou status reais da partida $t$ antes do fechamento do mercado constituiria vazamento grave, inviabilizando o modelo em ambiente produtivo.
* **Eliminação de Redundâncias e Multicolinearidade:**
  * `pontos_num_lag1`: Descartada para evitar colinearidade estrita com `feat_pontos_lag1` (que já inclui tratamento robusto de *Cold Start*).
  * `taxa_presenca_ewma5`: Descartada para evitar redundância com `minutos_ewma5`, que já pondera a minutagem real contínua.

### 2. O Lado das Colunas Utilizadas (Matriz Preditiva Pré-Jogo de 33 Features)

As variáveis selecionadas foram construídas para capturar a forma do atleta, força dos clubes e contexto tático, utilizando exclusivamente janelas defasadas:

| Grupo Temático | Variáveis Utilizadas (`cols_to_predict`) | Racional e Significado de Negócio |
| :--- | :--- | :--- |
| **Mercado e Contexto Básico (Defasados)** | `preco_num_lag1`, `variacao_num_lag1`, `media_num_lag1`, `jogos_num_lag1`, `status_pre`, `status_inicial`, `home_dummy`, `posicao_id`, `is_rodada_1` | Informações de mercado e situação pré-jogo conhecidas antes da rodada, defasadas em $t-1$ para evitar contaminação pós-jogo. |
| **Força Coletiva e Vulnerabilidade Rival (L5)** | `clube_media_pts_feitos_l5`, `adv_media_pts_cedidos_l5` | Médias móveis dos últimos 5 jogos do volume de pontos produzidos pelo clube e cedidos pelo oponente, com *fallback* histórico anual. |
| **Momento Individual com Cold Start** | `feat_pontos_lag1`, `feat_pontos_lag2`, `feat_media_pontos_3j`, `feat_media_pontos_5j`, `feat_std_pontos_5j` | Lags pontuais ($t-1, t-2$), médias móveis (3 e 5 jogos) e volatilidade individual, com imputação hierárquica histórica para estreantes (*Cold Start*). |
| **Decomposição Tática de Scouts (EWMA 5)** | `piso_ewma5`, `teto_ewma5`, `chutes_ewma5`, `pts_piso_gol_ewma5`, `disciplina_ewma5` | Médias exponenciais (span=5) separando regularidade defensiva (Piso), explosão ofensiva (Teto), volume de finalizações e risco disciplinar. |
| **Confiabilidade Física e Relatividade Posicional** | `minutos_ewma5`, `ratio_teto_piso`, `taxa_conversao_l5`, `piso_zscore_posicao` | Minutagem recente ponderada, relação teto/piso, eficiência na conversão de chutes em gols e normalização estatística ($Z$-score) do piso dentro da posição. |
| **Especializações Setoriais (Meias e Volantes via EWMA 3)** | `taxa_criacao_armacao`, `perfil_volante_intensidade`, `armacao_ewma3`, `intensidade_ewma3`, `is_meia_armador` | Ratios normalizados por tempo de jogo para capturar o perfil de armação (assistências + faltas sofridas) e intensidade de marcação (desarmes + faltas cometidas). |
| **Regimes de Temporada (Dummies)** | `regime_1turno`, `regime_2turno`, `regime_reta_final` | Codificação *one-hot* das fases do campeonato (Arranque como categoria base, Corpo 1º Turno, Corpo 2º Turno e Reta Final), capturando dinâmicas sazonais. |

---

## Questão 4: Que métricas você usou para avaliar o modelo, e por quê? O resultado obtido justifica colocar a solução em uso?

### 1. Métricas Utilizadas e Resultados na Safra de Teste Out-of-Sample (Safra 2025 - $N = 27.832$)

Para avaliar tanto a **precisão numérica** quanto a **utilidade prática para escalação (ranqueamento)**, foram empregadas métricas complementares de regressão e ordenação na safra de teste (2025):

| Família | Modelo | MAE (Geral) | RMSE | $R^2$ | Spearman $\rho$ | Pearson $r$ | MAE Top 20% | Redução MAE vs Baseline |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Heurística** | Baseline (`media_num_lag1`) | $2.2078$ | $3.2441$ | $-0.1402$ | $0.3738$ | $0.3521$ | $3.4169$ | $0.00\%$ |
| **Linear Paramétrico** | Regressão Linear (OLS) | $1.5239$ | $2.5134$ | $0.3156$ | $0.5480$ | $0.5651$ | $3.2751$ | $30.98\%$ |
| **Linear Paramétrico** | Ridge Regression ($L_2$) | $1.5241$ | $2.5132$ | $0.3157$ | $0.5480$ | $0.5651$ | $3.2749$ | $30.97\%$ |
| **Árvores / Ensembles** | Random Forest | $1.4583$ | $2.4946$ | $0.3258$ | $0.5442$ | $0.5739$ | $3.3318$ | $33.95\%$ |
| **Árvores / Ensembles** | CatBoost Regressor | $1.4624$ | $2.4787$ | $0.3344$ | $0.5540$ | $0.5798$ | $3.3168$ | $33.76\%$ |
| **Árvores / Ensembles** | XGBoost Regressor | $1.4535$ | $2.4662$ | $0.3411$ | $0.5618$ | $0.5858$ | $3.2869$ | $34.16\%$ |
| 🏆 **Árvores / Ensembles** | **LightGBM (Modelo Campeão)** | **$1.4541$** | **$2.4704$** | **$0.3388$** | **$0.5574$** | **$0.5842$** | **$3.2941$** | **$34.14\%$** |

#### Justificativa das Métricas:
* **MAE ($1.4541\text{ pts}$):** Mede o erro médio absoluto na mesma escala de pontuação do jogo. Proporcionou uma redução de **mais de $34\%$ no erro** em relação à média simples do mercado.
* **RMSE ($2.4704\text{ pts}$):** Penaliza desvios severos (goleadas atípicas ou expulsões não antecipadas).
* **$R^2$ ($0.3388$):** O modelo captura cerca de $34\%$ de toda a variância da pontuação em uma base completa com 27.832 registros (incluindo atletas reservas e nulos).
* **Spearman $\rho$ ($0.5574$) e Pearson $r$ ($0.5842$):** Comprovam forte concordância na ordenação relativa dos atletas, assegurando que o ranking de recomendações é altamente aderente ao desempenho real.
* **MAE Top 20% ($3.2941\text{ pts}$):** Avalia a precisão especificamente no grupo dos atletas mais pontuadores da rodada (os mais visados para escalação).

---

### 2. Por que o LightGBM foi selecionado como Modelo Campeão em vez do XGBoost?

Embora o XGBoost tenha apresentado uma métrica numérica marginalmente superior ($MAE = 1.4535$ vs $1.4541$), a escolha do **LightGBM** como modelo produtivo definitivo fundamenta-se em uma decisão de **Engenharia de Software e Eficiência Operacional (Trade-off de MLOps)**:

1. **Paridade Prática de Performance:** O delta de apenas $0.0006\text{ pontos}$ de MAE é estatisticamente nulo no contexto de um jogo de futebol (onde as pontuações variam em frações decimais muito maiores).
2. **Velocidade de Treinamento e Inferência:** Graças à divisão de nós *Leaf-wise* orientada por histogramas (*GOSS* e *EFB*), o LightGBM executa o treinamento e a inferência em uma fração do tempo do XGBoost.
3. **Consumo de Memória e Leveza de Artefato:** O modelo LightGBM serializado (`.joblib`) é substancialmente mais compacto e consome menos memória RAM, viabilizando tempos de resposta extremamente baixos no *serving* via API FastAPI (`src/service/app.py`).

---

### 3. O resultado obtido justifica colocar a solução em uso?

**Sim, a solução sustenta o uso em produção, desde que acompanhada do desenho de produto adequado.**

#### Racional de Sustentação de Negócio:
1. **Superação Estrutural dos Indicadores Atuais:** A informação disponível no Cartola FC hoje baseia-se em médias simples descritivas (`media_num`, preço e últimos jogos). O modelo campeão supera o baseline em todas as dimensões, ajustando a expectativa pelo mando de campo, força defensiva do adversário e especialização tática.
2. **Alta Capacidade de Ranqueamento ($\rho \approx 0.56$):** Para o usuário final que está montando o time, o diferencial é a capacidade de discernir **se o Atleta A tem maior expectativa de pontuação que o Atleta B** naquela rodada específica.

#### Recomendações de Engenharia e Design de Produto:
* **Exposição com Faixas de Potencial / Incerteza:** O futebol possui volatilidade intrínseca inerente a eventos estocásticos raros (pênaltis, expulsões precoces, falhas individuais). Exibir uma previsão pontual determinística única (ex: *"Gabriel fará 6.04 pts"*) pode gerar falsa sensação de exatidão. Recomenda-se apresentar a pontuação acompanhada de uma **faixa de potencial** (ex: *"Expectativa: 6.0 pts [Faixa provável: 3.5 a 8.5 pts]"*) ou de um **Score de Potencial Gato Mestre**.
* **Evolução Arquitetural no Roadmap:** Para iterações futuras, recomenda-se explorar arquiteturas em dois estágios (*Two-Stage / Hurdle Model* com classificador de probabilidade de atuação $P(\text{joga})$ desacoplado do regressor de potencial condicional $E[Y \mid \text{joga}]$) e modelos de regressão quantílica para estimar diretamente os percentis $P_{10}$ e $P_{90}$.

---

### 4. Estratégia de MLOps & Monitoramento Contínuo em Produção

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
