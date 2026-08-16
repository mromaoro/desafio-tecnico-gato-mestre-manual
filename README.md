# desafio-tecnico-gato-mestre-manual
Desafio técnico para globo esporte no time do gato mestre


estrutura do repositório

├── data/
│   ├── raw/                 # base_case_gm.csv e dados brutos da API
│   └── processed/           # tabelas tratadas / feature store local
├── notebooks/
│   └── modelagem.ipynb      # Análise, experimentos e respostas às perguntas
├── src/
│   ├── api_client/          # Cliente resiliente da API (retries 429/503, paginação)
│   ├── data/                # Scripts de limpeza e junção de fontes
│   ├── features/            # Pipeline de feature engineering
│   ├── models/              # Treinamento, validação e inferência
│   └── service/             # Código da API de exposição das previsões
├── outputs/
│   └── previsoes.json       # Contrato de saída final
├── presentation/            # Material da apresentação
├── tests
├── requirements.txt / pyproject.toml
└── README.md


testes:
test_service.py / test_contract.py (Contrato de Saída e API de Serving)
test_features.py / test_data.py (Engenharia de Dados e Features)
test_api_client.py (Resiliência da Ingestão)