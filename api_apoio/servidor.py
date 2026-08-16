"""
API de dados esportivos — apoio ao desafio técnico.

Serviço local de consulta a partidas, escalações e confrontos. Reproduz o
contrato da API interna de esportes: envelope com `resultados`, `referencias` e
`paginacao`, autenticação por header `token`, paginação por cursor e
instabilidade intermitente.

Depende apenas da biblioteca padrão do Python 3.10 ou superior.

Execução:
    python api_apoio/servidor.py

    curl -H "token: SEU_TOKEN" "http://localhost:8080/jogos?edicao=2025&rodada=1"
"""

import argparse
import json
import random
import re
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

RAIZ = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

PORTA_PADRAO = 8080
TOKEN_PADRAO = "gm-0e9ba73c2c96"

POR_PAGINA_PADRAO = 50
POR_PAGINA_MAXIMO = 300

# Limite folgado: existe para que o candidato precise tratar o 429, não para
# tornar o consumo penoso. Uma rotina bem construída não deve esbarrar nele.
RATE_LIMITE = 600
RATE_JANELA_SEGUNDOS = 60

# Instabilidade intermitente. Um consumo simples completa na maioria das vezes;
# volumes maiores exigem tratamento de erro.
PROB_FALHA = 0.03

MENSAGEM_SOBRECARGA = (
    "Nossos servidores estão sobrecarregados no momento. Tente novamente em breve."
)

CONFIG = {
    "token": TOKEN_PADRAO,
    "prob_falha": PROB_FALHA,
    "rate_limite": RATE_LIMITE,
}

DADOS = {}
_requisicoes = deque()


class ErroHTTP(Exception):
    def __init__(self, status, mensagem, cabecalhos=None):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem
        self.cabecalhos = cabecalhos or {}


# ---------------------------------------------------------------------------
# Regras de acesso
# ---------------------------------------------------------------------------

def validar_token(cabecalhos):
    token = cabecalhos.get("token")
    if token != CONFIG["token"]:
        raise ErroHTTP(401, "Token de acesso ausente ou inválido. "
                            "Informe o header `token` conforme a documentação.")


def aplicar_rate_limit():
    agora = time.time()
    while _requisicoes and agora - _requisicoes[0] > RATE_JANELA_SEGUNDOS:
        _requisicoes.popleft()

    if len(_requisicoes) >= CONFIG["rate_limite"]:
        espera = int(RATE_JANELA_SEGUNDOS - (agora - _requisicoes[0])) + 1
        raise ErroHTTP(
            429,
            f"Limite de requisições excedido. Tente novamente em {espera}s.",
            {"Retry-After": str(espera)},
        )

    _requisicoes.append(agora)


def simular_instabilidade():
    if random.random() < CONFIG["prob_falha"]:
        raise ErroHTTP(503, MENSAGEM_SOBRECARGA)


# ---------------------------------------------------------------------------
# Envelope e paginação
# ---------------------------------------------------------------------------

def envelope(resultados, referencias=None, paginacao=None):
    return {
        "resultados": resultados,
        "referencias": referencias or {},
        "paginacao": paginacao or {"anterior": None, "proximo": None},
    }


def paginar(itens, pagina, por_pagina, caminho):
    por_pagina = min(max(por_pagina, 1), POR_PAGINA_MAXIMO)
    inicio = (pagina - 1) * por_pagina
    recorte = itens[inicio:inicio + por_pagina]

    separador = "&" if "?" in caminho else "?"
    tem_proximo = inicio + por_pagina < len(itens)

    return recorte, {
        "anterior": (f"{caminho}{separador}pagina={pagina - 1}&por_pagina={por_pagina}"
                     if pagina > 1 else None),
        "proximo": (f"{caminho}{separador}pagina={pagina + 1}&por_pagina={por_pagina}"
                    if tem_proximo else None),
        "total": len(itens),
    }


def inteiro(parametros, nome, padrao=None, obrigatorio=False):
    valores = parametros.get(nome)
    if not valores:
        if obrigatorio:
            raise ErroHTTP(400, f"O parâmetro `{nome}` é obrigatório.")
        return padrao
    try:
        return int(valores[0])
    except ValueError:
        raise ErroHTTP(400, f"O parâmetro `{nome}` deve ser um número inteiro.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def listar_jogos(parametros):
    """Partidas de uma temporada, opcionalmente filtradas por rodada."""
    edicao = inteiro(parametros, "edicao", obrigatorio=True)
    rodada = inteiro(parametros, "rodada")
    pagina = inteiro(parametros, "pagina", 1)
    por_pagina = inteiro(parametros, "por_pagina", POR_PAGINA_PADRAO)

    jogos = [j for j in DADOS["jogos"] if j["edicao"] == edicao]
    if rodada is not None:
        jogos = [j for j in jogos if j["rodada"] == rodada]

    caminho = f"/jogos?edicao={edicao}"
    if rodada is not None:
        caminho += f"&rodada={rodada}"

    recorte, paginacao = paginar(jogos, pagina, por_pagina, caminho)

    return envelope(
        {"jogos": recorte},
        referencias={"equipes": DADOS["equipes"]},
        paginacao=paginacao,
    )


def obter_jogo(jogo_id):
    """Detalhe de uma partida, com a escalação das duas equipes."""
    jogo = DADOS["jogos_por_id"].get(str(jogo_id))
    if not jogo:
        raise ErroHTTP(404, f"Jogo {jogo_id} não encontrado.")

    # Nem toda partida tem escalação registrada; nesses casos a chave vem
    # ausente, e não como uma lista vazia.
    referencias = {"equipes": DADOS["equipes"]}
    escalacao = DADOS["escalacoes"].get(str(jogo_id))
    if escalacao:
        referencias["escalacao"] = escalacao

    return envelope({"jogo": jogo}, referencias=referencias)


def listar_equipes():
    """Cadastro das equipes participantes."""
    return envelope({"equipes": list(DADOS["equipes"].values())})


def obter_atleta(atleta_id):
    """Cadastro de um atleta: posição e clube."""
    atleta = DADOS["atletas"].get(str(atleta_id))
    if not atleta:
        raise ErroHTTP(404, f"Atleta {atleta_id} não encontrado.")

    return envelope({"atleta": atleta}, referencias={"equipes": DADOS["equipes"]})


def listar_confrontos(parametros):
    """Panorama de confrontos de uma rodada."""
    temporada = inteiro(parametros, "temporada", obrigatorio=True)
    rodada = inteiro(parametros, "rodada", obrigatorio=True)

    confrontos = DADOS["confrontos"].get(f"{temporada}/{rodada}")
    if not confrontos:
        raise ErroHTTP(404, "Não há dados de confronto para a temporada "
                            f"{temporada}, rodada {rodada}.")

    return envelope({"confrontos": confrontos})


ROTA_JOGO = re.compile(r"^/jogos/(\d+)$")
ROTA_ATLETA = re.compile(r"^/atletas/(\d+)$")


def rotear(caminho, parametros):
    if caminho == "/jogos":
        return listar_jogos(parametros)
    if caminho == "/equipes":
        return listar_equipes()
    if caminho == "/confrontos":
        return listar_confrontos(parametros)

    correspondencia = ROTA_JOGO.match(caminho)
    if correspondencia:
        return obter_jogo(int(correspondencia.group(1)))

    correspondencia = ROTA_ATLETA.match(caminho)
    if correspondencia:
        return obter_atleta(int(correspondencia.group(1)))

    raise ErroHTTP(404, f"Recurso não encontrado: {caminho}")


# ---------------------------------------------------------------------------
# Servidor
# ---------------------------------------------------------------------------

class Manipulador(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, formato, *args):
        pass  # silencia o log padrão, ruidoso demais

    def responder(self, status, corpo, cabecalhos=None):
        conteudo = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(conteudo)))
        for chave, valor in (cabecalhos or {}).items():
            self.send_header(chave, valor)
        self.end_headers()
        self.wfile.write(conteudo)

    def do_GET(self):
        endereco = urlparse(self.path)
        caminho = endereco.path.rstrip("/") or "/"
        parametros = parse_qs(endereco.query)

        if caminho == "/health":
            return self.responder(200, {"status": "ok"})

        try:
            validar_token(self.headers)
            aplicar_rate_limit()
            simular_instabilidade()
            self.responder(200, rotear(caminho, parametros))
        except ErroHTTP as erro:
            self.responder(erro.status, {"erro": erro.mensagem}, erro.cabecalhos)
        except Exception as erro:  # noqa: BLE001
            self.responder(500, {"erro": f"Erro interno: {erro}"})


def localizar_dados() -> Path:
    """
    Localiza o arquivo de dados.

    Procura ao lado do próprio script e na pasta `dados/`, de modo a funcionar
    tanto no material distribuído quanto no repositório de origem.
    """
    aqui = Path(__file__).resolve().parent
    candidatos = [
        aqui / "api_dataset.json",
        aqui.parents[1] / "data" / "processed" / "api_dataset.json",
    ]
    for caminho in candidatos:
        if caminho.exists():
            return caminho
    return candidatos[0]


def carregar_dados(caminho: Path):
    if not caminho.exists():
        raise SystemExit(
            f"Conjunto de dados não encontrado em {caminho}.\n"
            "Verifique se o arquivo `api_dataset.json` acompanha o material do desafio."
        )
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def main():
    parser = argparse.ArgumentParser(description="API de dados esportivos")
    parser.add_argument("--porta", type=int, default=PORTA_PADRAO,
                        help=f"porta do serviço (padrão: {PORTA_PADRAO})")
    argumentos = parser.parse_args()

    global DADOS
    DADOS = carregar_dados(localizar_dados())

    servidor = ThreadingHTTPServer(("0.0.0.0", argumentos.porta), Manipulador)

    print(f"\nAPI de dados esportivos — http://localhost:{argumentos.porta}")
    print(f"  {len(DADOS['jogos']):,} jogos | {len(DADOS['equipes'])} equipes")
    print(f"\n  Token de acesso: {CONFIG['token']}")
    print(f"  Informe-o no header `token` de cada requisição.")
    print(f"\n  Exemplo:")
    print(f'    curl -H "token: {CONFIG["token"]}" \\')
    print(f'      "http://localhost:{argumentos.porta}/jogos?edicao=2025&rodada=1"')
    print(f"\n  O serviço ocupa este terminal enquanto estiver no ar.")
    print(f"  Trabalhe em outra janela e encerre aqui com Ctrl+C.\n")

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServiço encerrado.")
        servidor.shutdown()


if __name__ == "__main__":
    main()
