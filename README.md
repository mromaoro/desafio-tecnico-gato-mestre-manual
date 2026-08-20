# Gato Mestre | Desafio Técnico - Ciência de Dados

Repositório da solução desenvolvida para a **Previsão de Pontuação de Atletas** do Cartola FC / Gato Mestre (Grupo Globo).

---

## 📌 Acesso Rápido aos Entregáveis

* 📄 **Respostas Oficiais do Desafio:** [`docs/respostas_perguntas_desafio.md`](docs/respostas_perguntas_desafio.md)
* 📓 **Pipeline End-to-End Integrado:** [`notebooks/05_pipeline_end_to_end.ipynb`](notebooks/05_pipeline_end_to_end.ipynb)
* 🚀 **Guia da API de Serving (FastAPI):** [`docs/execucao_servico.md`](docs/execucao_servico.md)
* 💾 **Arquivo Oficial de Previsões (Safra 2025):** [`previsoes.json`](previsoes.json)

---

## 📁 Estrutura do Repositório

```text
├── data/
│   ├── raw/                 # Dados brutos da base_case_gm.csv e extrações da API de apoio
│   └── processed/           # Tabelas limpas e feature store local (.parquet e .csv)
├── docs/
│   ├── respostas_perguntas_desafio.md  # Respostas técnicas oficiais às questões do edital
│   └── execucao_servico.md            # Guia completo de execução e consumo da API de serving
├── models/                  # Modelos treinados (.joblib) e preprocessors
├── notebooks/               # Jornada metodológica e analítica completa
│   ├── 01_obtencao_dados.ipynb
│   ├── 02_limpeza_e_preparacao.ipynb
│   ├── 03_eda_e_feature_engineering.ipynb
│   ├── 04_modelagem_e_validacao.ipynb
│   └── 05_pipeline_end_to_end.ipynb
├── src/
│   ├── api_client/          # Cliente HTTP resiliente para a API de apoio (retries 429/503)
│   ├── data_processing/     # Pipelines de limpeza, saneamento e deduplicação
│   ├── features/            # Pipeline de Feature Engineering sem data leakage
│   ├── models/              # Módulo de split temporal, treino (LightGBM/XGBoost) e inferência
│   └── service/             # API FastAPI de serving das previsões em tempo real
├── tests/                   # Suíte de testes automatizados (pytest)
│   ├── test_contract.py     # Validação estrita do schema e tipos de previsoes.json
│   └── test_service.py      # Testes de integração dos endpoints da API
├── previsoes.json           # Contrato oficial de saída com as previsões da safra OOS 2025
├── requirements.txt         # Dependências do projeto
└── README.md
```

---

## 🚀 Guia Rápido de Execução

### 1. Configuração do Ambiente Virtual

```bash
# Criação do ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalação das dependências
pip install -r requirements.txt
```

---

### 2. Execução da API de Apoio (Dados Esportivos)

Para subir o serviço interno de contexto de partidas e atletas:

```bash
python api_apoio/servidor.py
```

---

### 3. Execução dos Notebooks de Modelagem

Os notebooks estão organizados em sequência lógica e reprodutível:

1. **`notebooks/01_obtencao_dados.ipynb`**: Diagnóstico exploratório, qualidade de dados e extração resiliente da API.
2. **`notebooks/02_limpeza_e_preparacao.ipynb`**: Saneamento de dados, resolução de IDs e tratamento de inconsistências.
3. **`notebooks/03_eda_e_feature_engineering.ipynb`**: Análise exploratória profunda e criação de 38 features pré-jogo (*sem data leakage*).
4. **`notebooks/04_modelagem_e_validacao.ipynb`**: Validação temporal estrita (*Out-of-Time 2025*), benchmarks lineares e ensembles de árvores.
5. **`notebooks/05_pipeline_end_to_end.ipynb`**: Execução do pipeline completo ponta a ponta (ingestão raw, limpeza, features, treino do LightGBM e geração do `previsoes.json`).

---

### 4. Execução da API de Serving de Previsões (Entregável 3)

Para subir o serviço que expõe as previsões no contrato oficial com filtros por rodada, atleta, clube e posição:

```bash
.venv/bin/uvicorn src.service.app:app --host 0.0.0.0 --port 8000 --reload
```

* **Swagger UI (Documentação Interativa):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Healthcheck:** [http://localhost:8000/health](http://localhost:8000/health)
* **Consulta com filtros:** [http://localhost:8000/previsoes?rodada_id=1&posicao_id=1](http://localhost:8000/previsoes?rodada_id=1&posicao_id=1)

*Consulte o guia detalhado em [`docs/execucao_servico.md`](docs/execucao_servico.md).*

---

### 5. Execução dos Testes Automatizados

Para rodar a suíte completa de testes de contrato e integração da API:

```bash
.venv/bin/pytest tests/ -v
```