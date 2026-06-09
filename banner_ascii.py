"""
banner_ascii.py — Gerador standalone do banner ASCII da Mission Control AI.

Uso:
    python banner_ascii.py                 # banner padrao
    python banner_ascii.py -fonts          # lista as 570+ fontes do PyFiglet
    python banner_ascii.py -font slant -text "Mission Control AI"
    python banner_ascii.py -demo           # demonstra 8 fontes lado a lado
"""
import sys

import pyfiglet
from rich.console import Console
from rich.align import Align
from rich.text import Text

console = Console()

FONTES_DEMO = [
    "ansi_shadow", "slant", "big", "standard",
    "banner3", "doom", "isometric1", "small",
]


def banner_padrao():
    """Banner oficial em duas linhas, estilo Claude Code (ciano + roxo)."""
    linha1 = pyfiglet.figlet_format("Global Solution", font="ansi_shadow")
    linha2 = pyfiglet.figlet_format("Mission Control AI", font="ansi_shadow")
    console.print(Align.center(Text(linha1, style="bold #A855F7")))
    console.print(Align.center(Text(linha2, style="bold #06B6D4")))
    console.print(Align.center(
        Text("── 2026.1 · Prompt Engineering and AI · FIAP ──", style="italic #8484A0")
    ))


def listar_fontes():
    fontes = sorted(pyfiglet.FigletFont.getFonts())
    console.print(f"[bold]{len(fontes)} fontes disponiveis:[/bold]")
    console.print(", ".join(fontes))


def testar_fonte(fonte, texto):
    try:
        arte = pyfiglet.figlet_format(texto, font=fonte)
    except pyfiglet.FontNotFound:
        console.print(f"[red]Fonte '{fonte}' nao encontrada.[/red]")
        return
    console.print(Text(arte, style="bold #06B6D4"))


def demo():
    for fonte in FONTES_DEMO:
        console.rule(f"[#A855F7]{fonte}")
        testar_fonte(fonte, "Mission AI")


def main(argv):
    if "-fonts" in argv:
        listar_fontes()
    elif "-demo" in argv:
        demo()
    elif "-font" in argv:
        fonte = argv[argv.index("-font") + 1] if "-font" in argv else "ansi_shadow"
        texto = argv[argv.index("-text") + 1] if "-text" in argv else "Mission Control AI"
        testar_fonte(fonte, texto)
    else:
        banner_padrao()


if __name__ == "__main__":
    main(sys.argv[1:])
