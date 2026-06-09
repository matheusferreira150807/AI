"""
src/alertas.py — Thresholds, regras de decisao e respostas automatizadas.

REGRA DE OURO DO DESAFIO (secao 13.2): a logica de "e critico ou nao" mora AQUI,
em Python — nao no prompt da IA. O modelo serve para EXPLICAR e CONTEXTUALIZAR,
nunca para substituir um `if`. Cada alerta carrega tambem a "resposta_automatica"
(acao que o sistema dispara sozinho) e o "impacto_terrestre" (o diferencial 2026.1).
"""
from __future__ import annotations

# Niveis de severidade (ordem importa: define o pior caso global)
OK, ATENCAO, CRITICO = "OK", "ATENCAO", "CRITICO"
_ORDEM = {OK: 0, ATENCAO: 1, CRITICO: 2}


def _nivel(valor, limites_atencao, limites_critico, sentido) -> str:
    """
    Classifica um valor em OK/ATENCAO/CRITICO.

    sentido="alto"  -> valores ALTOS sao ruins (ex.: temperatura, buffer).
    sentido="baixo" -> valores BAIXOS sao ruins (ex.: energia, saude do sensor).
    """
    if sentido == "alto":
        if valor >= limites_critico:
            return CRITICO
        if valor >= limites_atencao:
            return ATENCAO
        return OK
    else:  # baixo
        if valor <= limites_critico:
            return CRITICO
        if valor <= limites_atencao:
            return ATENCAO
        return OK


def avaliar(dados: dict) -> dict:
    """
    Recebe um snapshot de telemetria e devolve o diagnostico estruturado:

        {
          "severidade_global": "OK" | "ATENCAO" | "CRITICO",
          "alertas": [ {parametro, valor, unidade, nivel, mensagem,
                        resposta_automatica, impacto_terrestre}, ... ],
          "acoes_automaticas": [ "..." ]
        }

    A saida estruturada (dict) permite que tanto a UI quanto o prompt da IA
    consumam o mesmo diagnostico — e habilita o diferencial "saida estruturada".
    """
    alertas: list[dict] = []

    # --- 1. Energia disponivel (baixo = ruim) -----------------------------
    nivel = _nivel(dados["energia"], 35, 20, "baixo")
    if nivel != OK:
        alertas.append({
            "parametro": "energia",
            "valor": dados["energia"], "unidade": "%", "nivel": nivel,
            "mensagem": "Energia abaixo da margem segura de operacao.",
            "resposta_automatica": (
                "MODO ECONOMIA ATIVADO: sensor optico desligado, mantida apenas a "
                "cadeia termica (prioridade incendio)." if nivel == CRITICO else
                "Reduzindo cadencia de captura para preservar bateria."
            ),
            "impacto_terrestre": (
                "Sem energia o satelite para de fotografar a floresta: brigadas "
                "ficam sem imagem nova de focos ativos durante a janela critica."
            ),
        })

    # --- 2. Temperatura do payload optico (alto = ruim) -------------------
    nivel = _nivel(dados["temp_payload_optico"], 35, 50, "alto")
    if nivel != OK:
        alertas.append({
            "parametro": "temp_payload_optico",
            "valor": dados["temp_payload_optico"], "unidade": "C", "nivel": nivel,
            "mensagem": "Payload optico acima da temperatura de operacao.",
            "resposta_automatica": (
                "Reorientando satelite para reduzir exposicao solar do payload."
                if nivel == CRITICO else "Monitorando deriva termica do payload."
            ),
            "impacto_terrestre": (
                "Sensor optico superaquecido gera ruido nas imagens RGB+NIR usadas "
                "para confirmar visualmente os focos detectados pelo sensor termico."
            ),
        })

    # --- 3. Saude do sensor termico (baixo = ruim) — coracao da missao ----
    nivel = _nivel(dados["saude_sensor_termico"], 80, 70, "baixo")
    if nivel != OK:
        alertas.append({
            "parametro": "saude_sensor_termico",
            "valor": dados["saude_sensor_termico"], "unidade": "%", "nivel": nivel,
            "mensagem": "Sensor termico (deteccao de focos) degradado.",
            "resposta_automatica": (
                "Acionando calibracao do array termico e marcando deteccoes do ciclo "
                "como BAIXA CONFIANCA." if nivel == CRITICO else
                "Agendando rotina de calibracao no proximo eclipse."
            ),
            "impacto_terrestre": (
                "E o sensor que enxerga o fogo. Degradado, o INPE pode NAO detectar "
                "um incendio em estagio inicial — quando ainda da para conter."
            ),
        })

    # --- 4. Precisao de geolocalizacao (alto = ruim) ----------------------
    nivel = _nivel(dados["precisao_geo"], 60, 100, "alto")
    if nivel != OK:
        alertas.append({
            "parametro": "precisao_geo",
            "valor": dados["precisao_geo"], "unidade": "m", "nivel": nivel,
            "mensagem": "Erro de geolocalizacao acima do tolerado.",
            "resposta_automatica": (
                "Resincronizando referencia de atitude com estrelas-guia (star tracker)."
                if nivel == CRITICO else "Aplicando correcao fina de efemeride."
            ),
            "impacto_terrestre": (
                "Detectar o foco nao basta: se a coordenada estiver errada em >100 m, "
                "a brigada e despachada para o lugar errado da mata."
            ),
        })

    # --- 5. Buffer de imagens nao transmitidas (alto = ruim) --------------
    nivel = _nivel(dados["buffer_imagens"], 80, 95, "alto")
    if nivel != OK:
        alertas.append({
            "parametro": "buffer_imagens",
            "valor": dados["buffer_imagens"], "unidade": "%", "nivel": nivel,
            "mensagem": "Buffer de imagens proximo da saturacao.",
            "resposta_automatica": (
                "PRIORIZANDO DOWNLINK: pausando novas capturas ate liberar espaco."
                if nivel == CRITICO else "Antecipando janela de downlink na proxima passagem."
            ),
            "impacto_terrestre": (
                "Imagem que nao desce nao vira alerta. Buffer cheio = dado de foco "
                "preso em orbita enquanto o fogo avanca na Terra."
            ),
        })

    # --- 6. Evento operacional: foco de calor detectado (nao e falha) -----
    if dados.get("focos_detectados", 0) >= 10 and dados["saude_sensor_termico"] >= 70:
        alertas.append({
            "parametro": "focos_detectados",
            "valor": dados["focos_detectados"], "unidade": "focos", "nivel": ATENCAO,
            "mensagem": "Multiplos focos de calor detectados na passagem.",
            "resposta_automatica": (
                "Disparando NOTIFICACAO PRIORITARIA ao centro de controle ambiental "
                "(INPE) com coordenadas e horario dos focos."
            ),
            "impacto_terrestre": (
                "Este e o motivo de a missao existir: cada foco vira um aviso que pode "
                "acionar a brigada antes de o incendio sair de controle."
            ),
        })

    # Severidade global = pior nivel encontrado
    if not alertas:
        severidade = OK
    else:
        severidade = max(alertas, key=lambda a: _ORDEM[a["nivel"]])["nivel"]

    acoes = [a["resposta_automatica"] for a in alertas
             if a["nivel"] == CRITICO or a["parametro"] == "focos_detectados"]

    return {
        "severidade_global": severidade,
        "alertas": alertas,
        "acoes_automaticas": acoes,
    }


def formatar_legivel(diagnostico: dict) -> str:
    """Versao texto do diagnostico — usada na UI e injetada no prompt da IA."""
    icones = {OK: "[OK]", ATENCAO: "[!]", CRITICO: "[X]"}
    linhas = [f"Severidade global: {icones[diagnostico['severidade_global']]} "
              f"{diagnostico['severidade_global']}"]
    if not diagnostico["alertas"]:
        linhas.append("  Nenhum alerta — todos os parametros dentro do range nominal.")
    for a in diagnostico["alertas"]:
        linhas.append(
            f"  {icones[a['nivel']]} {a['parametro']} = {a['valor']}{a['unidade']} "
            f"-> {a['mensagem']}"
        )
        linhas.append(f"      acao: {a['resposta_automatica']}")
    return "\n".join(linhas)


if __name__ == "__main__":
    # Teste rapido com um cenario critico montado a mao
    exemplo = {
        "energia": 14.0, "temp_payload_optico": 5.0, "saude_sensor_termico": 96.0,
        "saude_sensor_optico": 95.0, "buffer_imagens": 40.0, "precisao_geo": 10.0,
        "focos_detectados": 47,
    }
    print(formatar_legivel(avaliar(exemplo)))
