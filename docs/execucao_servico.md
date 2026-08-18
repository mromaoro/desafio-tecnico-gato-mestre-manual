# Guia de Execução e Consumo da API de Serving de Previsões

Este documento fornece as instruções operacionais para inicialização, consumo e validação do **Serviço de Previsão de Pontuação de Atletas** do Gato Mestre, desenvolvido em **FastAPI** e servido via **Uvicorn**.

---

## 1. Inicialização do Serviço

Com o ambiente virtual ativado, execute o comando abaixo na raiz do projeto:

```bash
# Inicialização padrão na porta 8000 com live-reload habilitado
.venv/bin/uvicorn src.service.app:app --host 0.0.0.0 --port 8000 --reload
```

Ao iniciar, o serviço carrega e indexa em memória as **27.832 previsões** da safra de avaliação contidas no arquivo [`previsoes.json`](file:///Users/actdigital/Documents/desafio-tecnico-gato-mestre-manual/previsoes.json).

### 📖 Documentação Interativa (Swagger & Redoc)
Com o serviço no ar, acesse a documentação interativa no navegador:
* **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 2. Endpoints e Exemplos de Requisição

### 2.1. Healthcheck (`GET /health`)
Verifica a saúde operacional da API e metadados da safra.

**Chamada via cURL:**
```bash
curl -X GET "http://localhost:8000/health"
```

**Exemplo de Resposta (HTTP 200):**
```json
{
  "status": "healthy",
  "servico": "Gato Mestre - API de Serving de Previsões",
  "ano_safra": 2025,
  "total_previsoes": 27832,
  "rodadas_disponiveis": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37]
}
```

---

### 2.2. Consulta de Previsões com Filtros (`GET /previsoes`)
Permite consultar previsões combinando filtros por rodada, atleta, clube e posição tática, com controle de paginação (`limit` e `offset`).

#### Exemplo A: Previsões de Goleiros (`posicao_id=1`) na Rodada 10
**Chamada via cURL:**
```bash
curl -X GET "http://localhost:8000/previsoes?rodada_id=10&posicao_id=1&limit=5"
```

**Exemplo de Resposta (HTTP 200 - Contrato Oficial do Desafio):**
```json
{
  "total": 5,
  "total_disponivel": 20,
  "limit": 5,
  "offset": 0,
  "previsoes": [
    {
      "atleta_id": 10008,
      "ano": 2025,
      "rodada_id": 10,
      "clube_id": 102,
      "posicao_id": 1,
      "pontos_predito": 3.82,
      "data_predicao": "2026-08-18T05:45:34Z"
    },
    {
      "atleta_id": 10045,
      "ano": 2025,
      "rodada_id": 10,
      "clube_id": 115,
      "posicao_id": 1,
      "pontos_predito": 4.15,
      "data_predicao": "2026-08-18T05:45:34Z"
    }
  ]
}
```

#### Exemplo B: Previsões de um Clube Específico (`clube_id=105`)
```bash
curl -X GET "http://localhost:8000/previsoes?clube_id=105&rodada_id=1&limit=10"
```

---

### 2.3. Consulta por Atleta Específico (`GET /previsoes/{atleta_id}`)
Retorna todas as previsões da safra para o jogador informado.

**Chamada via cURL:**
```bash
curl -X GET "http://localhost:8000/previsoes/10004"
```

**Exemplo de Resposta (HTTP 200):**
```json
{
  "total": 37,
  "total_disponivel": 37,
  "limit": 100,
  "offset": 0,
  "previsoes": [
    {
      "atleta_id": 10004,
      "ano": 2025,
      "rodada_id": 1,
      "clube_id": 105,
      "posicao_id": 6,
      "pontos_predito": 4.09,
      "data_predicao": "2026-08-18T05:45:34Z"
    },
    {
      "atleta_id": 10004,
      "ano": 2025,
      "rodada_id": 6,
      "clube_id": 113,
      "posicao_id": 6,
      "pontos_predito": 4.46,
      "data_predicao": "2026-08-18T05:45:34Z"
    }
  ]
}
```

---

### 2.4. Resiliência: Consulta de Atleta Inexistente
Quando um atleta ou filtro não possui dados, a API responde HTTP 200 com payload estruturado vazio, prevenindo erros no aplicativo cliente:

```bash
curl -X GET "http://localhost:8000/previsoes?atleta_id=99999999"
```

**Resposta:**
```json
{
  "total": 0,
  "total_disponivel": 0,
  "limit": 100,
  "offset": 0,
  "previsoes": []
}
```

---

## 3. Exemplo de Integração em Python

### 3.1. Consulta Pontual com Filtros
Script em Python demonstrando como o aplicativo do Cartola ou dashboards consom o serviço:

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Healthcheck
health = requests.get(f"{BASE_URL}/health").json()
print(f"Status do Serviço: {health['status']} | Total Previsões: {health['total_previsoes']}")

# 2. Previsão dos melhores atacantes da Rodada 20
params = {
    "rodada_id": 20,
    "posicao_id": 5, # Atacantes
    "limit": 10
}
res = requests.get(f"{BASE_URL}/previsoes", params=params).json()

print(f"\nTop Atacantes Previstos para a Rodada 20 (Total retornados: {res['total']}):")
for p in res["previsoes"]:
    print(f"  • Atleta {p['atleta_id']} (Clube {p['clube_id']}): {p['pontos_predito']:.2f} pts")
```

---

### 3.2. Como Consumir Todas as Previsões (Paginação Automática com Laço `while`)

Por motivos de performance e segurança de rede, a API utiliza **paginação baseada em cursor (`limit` e `offset`)** com teto de até 1.000 registros por requisição.

A resposta da API fornece os metadados necessários para controlar a iteração:
* `total_disponivel`: Volume total de registros que satisfazem os filtros informados.
* `total`: Quantidade de registros entregues na página atual.
* `offset`: Posição inicial da página atual.

Para recuperar a base completa (todas as 27.832 previsões ou todos os atletas de várias rodadas) em memória, utilize o padrão de laço abaixo:

```python
import requests

BASE_URL = "http://localhost:8000"

def obter_todas_as_previsoes(filtros: dict = None, tamanho_pagina: int = 500) -> list:
    """Itera automaticamente por todas as páginas da API até coletar 100% dos dados."""
    params = filtros.copy() if filtros else {}
    params["limit"] = min(tamanho_pagina, 1000) # Respeita o teto de 1000 por página
    params["offset"] = 0
    
    todas_previsoes = []
    
    while True:
        resposta = requests.get(f"{BASE_URL}/previsoes", params=params).json()
        previsoes_pagina = resposta.get("previsoes", [])
        total_disponivel = resposta.get("total_disponivel", 0)
        
        todas_previsoes.extend(previsoes_pagina)
        print(f"Progresso: {len(todas_previsoes)}/{total_disponivel} registros coletados...")
        
        params["offset"] += len(previsoes_pagina)
        
        # Condição de parada: quando não houver mais registros ou atingir o total disponível
        if not previsoes_pagina or params["offset"] >= total_disponivel:
            break
            
    return todas_previsoes

# Exemplo de uso: coletar todas as 27.832 previsões da safra
previsoes_completas = obter_todas_as_previsoes(tamanho_pagina=1000)
print(f"✅ Coleta finalizada: {len(previsoes_completas)} previsões prontas para uso.")
```

---

## 4. Execução dos Testes Automatizados

A suíte de testes automatizados valida o contrato de dados e todos os endpoints do serviço:

```bash
# Executa todos os testes unitários e de integração
.venv/bin/pytest tests/ -v
```
