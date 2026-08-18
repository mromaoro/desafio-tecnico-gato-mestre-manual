# Roteiro da Apresentação Técnica (60 Minutos)

**Gato Mestre | Previsão de Pontuação de Atletas**  
**Público-Alvo:** Time Técnico de Ciência de Dados e Engenharia de Machine Learning do Grupo Globo  
**Tempo Total:** 60 minutos (35-40 min de apresentação + 20 min de Q&A)  
**Apresentador:** Matheus Romão

---

## ⏱️ Estrutura de Tempo e Distribuição dos Slides

| Slide | Tema | Tempo Estimado | Foco Principal da Fala |
| :---: | :--- | :---: | :--- |
| **1** | Abertura e Visão Geral da Arquitetura | 3 min | Contexto de produto, esteira ponta a ponta e integridade amostral (115k atletas). |
| **2** | Auditoria da Base e Inconsistências (API Canônica) | 4 min | Como a API foi usada como *Single Source of Truth* para não descartar dados. |
| **3** | Prevenção a Data Leakage & Feature Engineering | 5 min | Regra de ouro do pré-jogo e matriz de 37 features defasadas de momento e confronto. |
| **4** | Evidência Estatística: O Poder de `status_pre` | 3 min | Testes ANOVA ($F = 8.703, \eta^2 = 22,8\%$) e Kruskal-Wallis como filtro de oportunidade. |
| **5** | Estratégia de Validação Temporal (*Out-of-Time*) | 4 min | Por que K-Fold é inadequado e por que isolar 2024 (Optuna) e 2025 (Teste OOS cego). |
| **6** | Comparativo de Modelos e Safra 2025 | 5 min | Evolução de performance (Baseline $\rightarrow$ OLS $\rightarrow$ Árvores $\rightarrow$ LightGBM Tunado). |
| **7** | Explicabilidade Física com SHAP Values | 4 min | Abrir a caixa preta: como o modelo aprendeu a física real do futebol (TreeSHAP). |
| **8** | Decisão de Negócio e Proposta de UX | 4 min | O modelo sustenta o lançamento? Poder de ranking ($\rho = 0.6011$) e faixas de potencial. |
| **9** | Engenharia de Serving e API FastAPI | 4 min | Padrão de serving em baixa latência, testes automatizados e contrato de saída. |
| **10** | MLOps & Observabilidade em Produção (Drift) | 4 min | Estratégia de detecção de Data Drift, Target Drift e Concept Drift pós-rodada. |
| **11** | Roadmap Técnico e Próximos Passos | 3 min | Two-Stage/Hurdle model, regressão quantílica, xG/xA e retreino contínuo. |
| **-** | **Sessão de Perguntas e Respostas (Q&A)** | **20 min** | Defesa técnica e aprofundamento nos trade-offs. |

---

## 🎙️ Roteiro de Fala Passo a Passo

### Slide 1: Abertura e Visão Executiva (3 min)
* **Objetivo:** Abrir a apresentação estabelecendo empatia com o desafio de negócio do Cartola FC e destacando a visão holística de engenharia e ciência de dados.
* **O que falar:**
  > *"Olá a todos. O objetivo deste trabalho foi construir uma solução completa, robusta e escalável para prever a pontuação dos atletas no Cartola FC antes do fechamento do mercado. Quando olhamos para um fantasy game com milhões de usuários, a precisão e o poder de ranqueamento da previsão influenciam diretamente a experiência de escalação.  
  Minha abordagem não foi apenas treinar um modelo isolado, mas desenhar uma esteira ponta a ponta: desde o consumo resiliente da API de apoio, passando por saneamento canônico, blindagem rigorosa contra vazamento temporal, validação temporal estrita e a disponibilização de uma API de serving assíncrona em FastAPI com testes automatizados."*

---

### Slide 2: Auditoria de Dados e Inconsistências (4 min)
* **Objetivo:** Responder à Questão 1 e demonstrar como você tratou dados ruidosos sem recorrer a atalhos ingênuos de descarte.
* **O que falar:**
  > *"Ao analisar a base bruta de 117 mil linhas, identifiquei 7 inconsistências estruturais. Em vez de simplesmente deletar registros com posições estranhas (como 0, 7 ou 9) ou com mandos e oponentes nulos (cerca de 12% da base), utilizei a API oficial de apoio como fonte primária da verdade.  
  Cruzando os dados de partidas e atletas, recalculamos o mando com exatidão matemática, recuperamos o adversário real, saneamos a coluna de preços eliminando sinais negativos e corrigimos a minutagem através das súmulas oficiais de substituição. O resultado foi uma base 100% limpa, íntegra e sem perda amostral arbitrária."*

---

### Slide 3 e 4: Barreira Temporal e o Sinal de `status_pre` (8 min)
* **Objetivo:** Responder à Questão 3 e justificar a engenharia de variáveis com rigor estatístico.
* **O que falar:**
  > *"A regra de ouro que guiou toda a engenharia de variáveis foi: 'Zero Data Leakage'. Nenhuma variável apurada durante ou após os 90 minutos de jogo (como scouts da partida, minutos jogados reais ou variação de preço) pôde entrar no instante $t$.  
  Transformamos o histórico em 37 variáveis defasadas: médias móveis ponderadas de 3 e 5 jogos, momento de preço e métricas de confronto (como o fator de alavancagem entre o ataque do time e a fragilidade defensiva do adversário).  
  Além disso, validamos estatisticamente o status pré-jogo: através de ANOVA e Kruskal-Wallis, comprovamos que `status_pre` sozinho responde por quase 23% de toda a variância dos pontos, funcionando como um filtro natural de probabilidade de participação."*

---

### Slide 5: Estratégia de Validação Temporal Estrita (4 min)
* **Objetivo:** Responder à Questão 2 e defender a escolha da divisão temporal anual.
* **O que falar:**
  > *"Para validar os modelos, o uso de K-Fold aleatório foi sumariamente descartado, pois em séries temporais esportivas ele causa vazamento de dados do futuro para o passado.  
  Estruturei uma validação temporal estrita por safras anuais: 2022 e 2023 para Treino (59k registros), 2024 para Validação e Tuning Bayesiano de Hiperparâmetros no Optuna (28k registros), e 2025 completamente isolada como Teste Out-of-Sample cego (27k registros). Essa separação garante que a performance medida em 2025 reflete a capacidade real do modelo de generalizar para novos elencos e dinâmicas táticas."*

---

### Slide 6 e 7: Benchmarks e Explicabilidade SHAP (9 min)
* **Objetivo:** Responder à Questão 4 (parte técnica) e mostrar que o modelo não é uma caixa preta.
* **O que falar:**
  > *"Avaliando os modelos cegamente na safra 2025 com 27.832 atletas, construímos uma esteira evolutiva. A média simples do app tem MAE de 2.31 pts e R² nulo. Os modelos lineares melhoraram para 1.72 pts. O campeão definitivo foi o LightGBM tunado, alcançando MAE de 1.4103 pts, R² de 0.3451 e uma correlação de ranking Spearman de 0.6011.  
  Para garantir a governança e auditar a lógica interna do modelo, aplicamos o TreeSHAP. O gráfico de SHAP confirmou que as decisões respeitam a lógica do futebol: o principal vetor é o potencial esperado do atleta modulado pelo confronto, seguido da probabilidade de escalação e da regularidade de scouts de volume."*

---

### Slide 8 e 9: Decisão de Negócio, UX e Serving (8 min)
* **Objetivo:** Responder à Questão 4 (parte de produto) e apresentar a entrega de engenharia de software.
* **O que falar:**
  > *"O resultado justifica colocar a solução em produção? Sim, porque o modelo tem uma forte capacidade de ranqueamento (Spearman 0.60), que é exatamente o que o usuário precisa para decidir entre escalar o Atleta A ou o Atleta B.  
  Porém, a recomendação de produto é nunca exibir uma predição pontual determinística como verdade absoluta. O futebol tem variância intrínseca (pênaltis, expulsões). Recomendamos exibir a previsão com uma faixa de potencial (ex: 5.8 pts [Faixa: 3.5 a 8.5 pts]).  
  Por fim, construí a API de serving em FastAPI com Uvicorn, indexando as 27.832 previsões em memória para entregar consultas filtradas em milissegundos, com 13 testes automatizados garantindo a conformidade do contrato de dados."*

---

### Slide 10: MLOps e Monitoramento Contínuo de Drift (4 min)
* **Objetivo:** Demonstrar senioridade em sustentação de modelos e acompanhamento contínuo de métricas.
* **O que falar:**
  > *"Colocar o modelo em produção é apenas metade do trabalho. Para garantir a sustentabilidade, desenhei a estratégia de observabilidade baseada em três tipos de drift:  
  1. Data Drift (Covariate Shift): Monitoramos via Population Stability Index (PSI > 0.20) e testes Kolmogorov-Smirnov a chegada de novos reforços e alterações de preço na janela de meio de ano.  
  2. Target Drift: Acompanhamos a distância de Wasserstein na distribuição de pontuações reais da liga para detectar mudanças de regime no campeonato.  
  3. Concept Drift: Acompanhamos pós-rodada o MAE e o Spearman daquela rodada. Se o erro subir mais de 30% em relação ao baseline de 1.41, um alerta dispara o pipeline automatizado de retreino (Rolling Retraining)."*

---

### Slide 11: Roadmap Técnico e Encerramento (3 min)
* **O que falar:**
  > *"Como próximos passos para o Gato Mestre, proponho explorarmos uma arquitetura em dois estágios (Hurdle Model) para desacoplar a probabilidade de entrar em campo do potencial condicional de pontos, além de regressão quantílica para estimar diretamente os percentis P10 e P90.  
  Agradeço a atenção de todos e abro agora para nossa discussão técnica."*

---

## 🎯 Guia de Respostas para o Q&A Técnico (Perguntas Prováveis da Banca)

### Pergunta 1: *"Por que vocês escolheram o LightGBM em vez de uma Rede Neural Tabular ou XGBoost?"*
* **Resposta Recomendada:** O LightGBM demonstrou o melhor trade-off entre performance empírica (menor MAE e maior $R^2$), suporte nativo a variáveis categóricas de alta cardinalidade via partição ótima de Fisher (`clube_id`, `opponent`, `posicao_id`) e velocidade de inferência ($<1\text{ms}$ por predição), sendo ideal para o ecossistema de produção do Cartola.

### Pergunta 2: *"Como vocês monitoram se o modelo parou de funcionar no meio do Brasileirão?"*
* **Resposta Recomendada:** Através de observabilidade contínua pós-rodada: monitoramos o MAE semanal e a correlação de Spearman intra-rodada. Se o Spearman cair abaixo de 0.40 ou houver forte Data Drift (PSI > 0.25 em virtude da janela de transferências), o pipeline de CI/CD aciona o retreino automático incorporando as últimas rodadas.

### Pergunta 3: *"Por que não treinar o modelo apenas com quem entrou em campo?"*
* **Resposta Recomendada:** Treinar apenas com quem jogou geraria *Viés de Sobrevivência* e impossibilitaria o produto de precificar o risco de não-atuação para os milhões de usuários que consultam o catálogo completo. O modelo aprendeu a calibrar o valor esperado $E[Y] = P(\text{atua}) \times \text{Pontos}$.
