"""
src/engine.py — Motor de analise da Mission Control AI (trilha EnviroSat).

Combina:
  (a) a funcao llm() — ponto unico de contato com a IA (Ollama Cloud);
  (b) a classe MissionEngine — coleta telemetria, avalia alertas em Python,
      monta o prompt com dados REAIS injetados e chama o LLM.

Diferenciais implementados (secao 5.3):
  - Injecao dinamica da telemetria no prompt (nao hardcoded).
  - Memoria de contexto: os ultimos ciclos sao passados a IA (consciencia temporal).
  - Saida estruturada da camada de alertas (dict) consumida pelo prompt.
"""
from __future__ import annotations

import os
from pathlib import Path
from collections import deque

from ollama import Client
from dotenv import load_dotenv

from src import telemetria, alertas

load_dotenv()

# Identificacao da trilha — ALTEREM conforme a escolha do grupo
TRILHA = "envirosat"  # "agrosat" | "envirosat" | "connectsat" | "mobilitysat"

client = Client(
    host="https://ollama.com",
    headers={"Authorization": "Bearer " + os.environ.get("OLLAMA_API_KEY", "")},
)

_api = os.environ.get("OLLAMA_API_KEY")
print("API KEY carregada:", "OK" if _api else "FALTANDO")


def llm(prompt, system=None, max_tokens=800, temperature=0.3):
    """Envia prompt ao gpt-oss:120b via Ollama Cloud e retorna texto.

    Ponto UNICO de integracao com a IA (secao 4.2). Toda chamada passa por aqui.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        return client.chat(
            model="gpt-oss:120b",
            messages=messages,
            options={"num_predict": max_tokens, "temperature": temperature},
            stream=False,
        )["message"]["content"].strip()
    except Exception as e:  # noqa: BLE001 — devolve erro amigavel em vez de quebrar a CLI
        return f"[!] Erro ao consultar IA: {e}"


def load_system_prompt():
    """Le o system prompt do arquivo prompts/system_prompt.md."""
    path = Path("prompts/system_prompt.md")
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "Voce e um assistente."  # fallback generico


class MissionEngine:
    """Motor de analise — orquestra telemetria + alertas + IA."""

    def __init__(self):
        self.trilha = TRILHA
        self.system_prompt = load_system_prompt()
        self.ultimo_snapshot: dict | None = None
        self.ultimo_diagnostico: dict | None = None
        # Memoria de contexto: ultimos 5 ciclos (diferencial "consciencia temporal")
        self.historico: deque = deque(maxlen=5)

    # -- estado -----------------------------------------------------------
    def is_ready(self):
        return True  # analyze() implementado

    def _coletar_ciclo(self, cenario: str | None = None):
        """Coleta um ciclo, avalia alertas e atualiza a memoria de contexto."""
        dados = telemetria.coletar(cenario)
        diagnostico = alertas.avaliar(dados)
        self.ultimo_snapshot = dados
        self.ultimo_diagnostico = diagnostico
        self.historico.append({
            "ciclo": dados["ciclo"],
            "severidade": diagnostico["severidade_global"],
            "focos": dados["focos_detectados"],
            "energia": dados["energia"],
        })
        return dados, diagnostico

    def status_snapshot(self):
        """Resumo legivel do estado atual da telemetria (comando /status)."""
        dados, diagnostico = self._coletar_ciclo()
        return (
            telemetria.formatar_legivel(dados)
            + "\n\n"
            + alertas.formatar_legivel(diagnostico)
        )

    # -- nucleo da analise ------------------------------------------------
    def _detectar_cenario(self, pergunta: str) -> str | None:
        """Permite o usuario forcar um cenario de teste pela propria pergunta.

        Ex.: 'simule incendio', 'cenario bateria_critica'. Caso contrario,
        usa a telemetria ao vivo.
        """
        p = pergunta.lower()
        mapa = {
            "incendio": "incendio_amazonia",
            "fogo": "incendio_amazonia",
            "bateria": "bateria_critica",
            "energia": "bateria_critica",
            "sensor termico": "falha_sensor_termico",
            "superaquec": "sobreaquecimento",
            "geolocal": "perda_geolocalizacao",
            "buffer": "buffer_cheio",
        }
        for chave, cenario in mapa.items():
            if chave in p:
                return cenario
        return None

    def _montar_prompt(self, pergunta: str, dados: dict, diagnostico: dict) -> str:
        """Monta o prompt do usuario com a telemetria REAL injetada dinamicamente."""
        hist = "\n".join(
            f"  ciclo {h['ciclo']}: sev={h['severidade']} focos={h['focos']} "
            f"energia={h['energia']}%"
            for h in self.historico
        ) or "  (primeiro ciclo)"

        return (
            "Você recebeu um novo ciclo de telemetria do EnviroSat-1.\n\n"
            "=== TELEMETRIA DO CICLO ATUAL ===\n"
            f"{telemetria.formatar_legivel(dados)}\n\n"
            "=== DIAGNOSTICO DA LOGICA (Python, ja classificado) ===\n"
            f"{alertas.formatar_legivel(diagnostico)}\n\n"
            "=== HISTORICO DOS ULTIMOS CICLOS ===\n"
            f"{hist}\n\n"
            "=== PERGUNTA DO OPERADOR ===\n"
            f"{pergunta}\n\n"
            "Responda no formato definido no system prompt, usando SOMENTE os "
            "numeros acima e amarrando cada ponto ao impacto terrestre."
        )

    def analyze(self, pergunta_usuario):
        """Analisa a pergunta com base na telemetria + alertas + IA."""
        cenario = self._detectar_cenario(pergunta_usuario)
        dados, diagnostico = self._coletar_ciclo(cenario)
        prompt = self._montar_prompt(pergunta_usuario, dados, diagnostico)

        # Temperatura mais baixa em crise (resposta mais estavel/deterministica)
        temp = 0.2 if diagnostico["severidade_global"] == alertas.CRITICO else 0.4
        resposta_ia = llm(prompt, system=self.system_prompt, temperature=temp)

        # Cabecalho deterministico (do codigo) + analise contextual (da IA)
        cabecalho = (
            f"Ciclo {dados['ciclo']} | cenario: {dados['cenario']} | "
            f"severidade: {diagnostico['severidade_global']}"
        )
        acoes = ""
        if diagnostico["acoes_automaticas"]:
            acoes = "\nAcoes automaticas disparadas pelo sistema:\n" + "\n".join(
                f"  - {a}" for a in diagnostico["acoes_automaticas"]
            )
        return f"{cabecalho}{acoes}\n\n{resposta_ia}"
