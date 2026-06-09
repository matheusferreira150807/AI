"""Interface CLI estilo Claude Code — usa Rich + prompt-toolkit (trilha EnviroSat)."""
from datetime import datetime

import pyfiglet
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

console = Console()
session = PromptSession(style=Style.from_dict({"prompt": "#06B6D4 bold"}))

COMANDOS = {
    "/help": "Lista os comandos disponiveis",
    "/status": "Mostra um snapshot da telemetria atual + alertas",
    "/about": "Sobre a missao EnviroSat",
    "/clear": "Limpa a tela e redesenha o banner",
    "/exit": "Encerra a Mission Control AI",
}


def show_banner():
    """Exibe banner ASCII colorido no inicio."""
    banner = pyfiglet.figlet_format("Mission Control", font="ansi_shadow")
    console.print(Text(banner, style="bold #06B6D4"))
    console.print(Panel.fit(
        "[bold]EnviroSat-1[/bold] — observacao ambiental · deteccao de focos de calor\n"
        "Sistema de monitoramento e analise por IA generativa.\n"
        "Use [bold]/help[/bold] para ver os comandos · [bold]/exit[/bold] para sair.\n"
        "Modelo: gpt-oss:120b via Ollama Cloud",
        title="◆ MISSION CONTROL", border_style="#06B6D4", subtitle="connected",
    ))


def show_help():
    tabela = Table(title="Comandos disponiveis", border_style="#06B6D4",
                   title_style="bold #06B6D4")
    tabela.add_column("Comando", style="bold #A855F7")
    tabela.add_column("Descricao")
    for cmd, desc in COMANDOS.items():
        tabela.add_row(cmd, desc)
    console.print(tabela)
    console.print(
        "Dica: voce pode forcar cenarios de teste na pergunta — ex.: "
        "[italic]\"simule um incendio\"[/italic], [italic]\"e a bateria?\"[/italic], "
        "[italic]\"problema de geolocalizacao\"[/italic].",
        style="#8484A0",
    )


def show_about():
    console.print(Panel(
        "EnviroSat-1 e um satelite simulado de observacao ambiental, classe "
        "Amazonia-1 / Landsat, com sensor termico (focos) e optico RGB+NIR.\n\n"
        "Personas atendidas: operador de centro de controle (INPE), coordenador "
        "de brigada de combate a incendio e analista de compliance ambiental.\n\n"
        "Setor de impacto: sustentabilidade e clima — combate ao desmatamento e "
        "resposta rapida a incendios.",
        title="◆ Sobre a missao", border_style="#A855F7",
    ))


def show_response(text):
    """Renderiza resposta da IA em painel com timestamp."""
    now = datetime.now().strftime("%H:%M")
    console.print(Panel(text, title="◆ Mission Control",
                        subtitle=now, border_style="#06B6D4"))


def run_cli(engine):
    """Loop principal da CLI."""
    show_banner()
    if not engine.is_ready():
        console.print("  ⚠ Engine status: AGUARDANDO IMPLEMENTACAO ✗\n", style="yellow")
    else:
        console.print("  ✓ Engine status: OPERACIONAL\n", style="green")

    while True:
        try:
            user_input = session.prompt("❯ ").strip()
        except (KeyboardInterrupt, EOFError):
            break
        if not user_input:
            continue
        if user_input == "/exit":
            console.print("Encerrando Mission Control. Boa missao!", style="#06B6D4")
            break
        if user_input == "/help":
            show_help()
            continue
        if user_input == "/about":
            show_about()
            continue
        if user_input == "/status":
            show_response(engine.status_snapshot())
            continue
        if user_input == "/clear":
            console.clear()
            show_banner()
            continue
        # Qualquer outra entrada vai para o motor de analise
        with console.status("[#06B6D4]Analisando telemetria com a IA...", spinner="dots"):
            resposta = engine.analyze(user_input)
        show_response(resposta)
