"""
src/telemetria.py — Geracao dos dados simulados do satelite EnviroSat.

EnviroSat e um satelite de observacao ambiental (similar a Amazonia-1 / Landsat)
com sensor termico (deteccao de focos de incendio) e sensor optico RGB+NIR.

Os dados NAO precisam ser cientificamente exatos — precisam ser PLAUSIVEIS e
COERENTES com a missao (requisito da secao 7). A simulacao mantem estado entre
ciclos para permitir series temporais e "memoria de contexto" no engine.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Faixas nominais de cada parametro (usadas tambem pelos alertas em alertas.py)
# ---------------------------------------------------------------------------
PARAMETROS = {
    "temp_payload_optico": {"unidade": "C",   "nominal": (-15.0, 25.0)},
    "saude_sensor_termico": {"unidade": "%",  "nominal": (85.0, 100.0)},
    "saude_sensor_optico": {"unidade": "%",   "nominal": (85.0, 100.0)},
    "buffer_imagens": {"unidade": "%",        "nominal": (0.0, 75.0)},
    "precisao_geo": {"unidade": "m",          "nominal": (0.0, 30.0)},
    "energia": {"unidade": "%",               "nominal": (40.0, 100.0)},
}

# Cenarios pre-definidos que FORCAM certos valores (testar casos extremos).
# Combinam com data/cenarios.json — aqui ficam os "presets" de codigo.
CENARIOS = {
    "normal": {},
    "incendio_amazonia": {
        "focos_detectados": 47,
        "saude_sensor_termico": 96.0,
        "buffer_imagens": 88.0,  # muitas imagens da area de foco para enviar
    },
    "falha_sensor_termico": {
        "saude_sensor_termico": 41.0,
        "focos_detectados": 0,  # nao consegue detectar com sensor degradado
    },
    "bateria_critica": {
        "energia": 14.0,
        "temp_payload_optico": 33.0,
    },
    "sobreaquecimento": {
        "temp_payload_optico": 58.0,
        "saude_sensor_optico": 62.0,
    },
    "perda_geolocalizacao": {
        "precisao_geo": 180.0,
        "focos_detectados": 12,  # detecta focos mas nao sabe ONDE (inutil!)
    },
    "buffer_cheio": {
        "buffer_imagens": 97.0,
        "energia": 28.0,
    },
}


@dataclass
class SimuladorEnviroSat:
    """Mantem o estado do satelite entre ciclos (drift suave + ruido)."""

    ciclo: int = 0
    estado: dict = field(default_factory=lambda: {
        "temp_payload_optico": 5.0,
        "saude_sensor_termico": 98.0,
        "saude_sensor_optico": 97.0,
        "buffer_imagens": 30.0,
        "precisao_geo": 12.0,
        "energia": 82.0,
        "focos_detectados": 3,
    })

    def _passo(self, chave: str, delta: float, minimo: float, maximo: float) -> None:
        """Aplica um passo aleatorio limitado, mantendo o valor no intervalo."""
        novo = self.estado[chave] + random.uniform(-delta, delta)
        self.estado[chave] = max(minimo, min(maximo, novo))

    def coletar(self, cenario: str | None = None) -> dict:
        """
        Retorna um snapshot da telemetria do ciclo atual.

        Se `cenario` for informado, os valores correspondentes sao forcados
        por cima da evolucao natural (util para demonstrar casos extremos).
        """
        self.ciclo += 1

        # Evolucao natural (drift + ruido) de cada parametro
        self._passo("temp_payload_optico", 4.0, -25.0, 70.0)
        self._passo("saude_sensor_termico", 1.5, 30.0, 100.0)
        self._passo("saude_sensor_optico", 1.5, 30.0, 100.0)
        self._passo("buffer_imagens", 8.0, 0.0, 100.0)
        self._passo("precisao_geo", 6.0, 2.0, 250.0)
        self._passo("energia", 5.0, 0.0, 100.0)
        self.estado["focos_detectados"] = max(
            0, int(self.estado["focos_detectados"] + random.randint(-2, 3))
        )

        # Aplica o cenario forcado, se houver
        if cenario and cenario in CENARIOS:
            for chave, valor in CENARIOS[cenario].items():
                self.estado[chave] = valor

        snapshot = {
            "satelite": "EnviroSat-1",
            "trilha": "envirosat",
            "ciclo": self.ciclo,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "cenario": cenario or "telemetria_ao_vivo",
            **{chave: round(self.estado[chave], 1) if isinstance(self.estado[chave], float)
               else self.estado[chave] for chave in self.estado},
        }
        return snapshot


# Instancia unica de modulo — o engine importa estas funcoes diretamente.
_simulador = SimuladorEnviroSat()


def coletar(cenario: str | None = None) -> dict:
    """Ponto de entrada usado pelo MissionEngine: coleta um ciclo de telemetria."""
    return _simulador.coletar(cenario)


def reset() -> None:
    """Reinicia o simulador (util em testes)."""
    global _simulador
    _simulador = SimuladorEnviroSat()


def formatar_legivel(dados: dict) -> str:
    """Versao texto humana de um snapshot — usada no /status e no prompt da IA."""
    return (
        f"Satelite: {dados['satelite']}  |  Ciclo: {dados['ciclo']}  |  "
        f"UTC: {dados['timestamp']}\n"
        f"  - Temp. payload optico ...... {dados['temp_payload_optico']} C\n"
        f"  - Saude sensor termico ...... {dados['saude_sensor_termico']} %\n"
        f"  - Saude sensor optico ....... {dados['saude_sensor_optico']} %\n"
        f"  - Buffer de imagens ......... {dados['buffer_imagens']} %\n"
        f"  - Precisao geolocalizacao ... {dados['precisao_geo']} m\n"
        f"  - Energia disponivel ........ {dados['energia']} %\n"
        f"  - Focos de calor detectados . {dados['focos_detectados']}"
    )


if __name__ == "__main__":
    # Teste rapido: 3 ciclos normais + 1 cenario de incendio
    for _ in range(3):
        print(formatar_legivel(coletar()), "\n")
    print(formatar_legivel(coletar("incendio_amazonia")))
