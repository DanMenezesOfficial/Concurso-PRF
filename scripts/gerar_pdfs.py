#!/usr/bin/env python3
"""Gera PDFs dos documentos Markdown (docs/ e docs/apostila/) em pdf/.

Uso: python3 scripts/gerar_pdfs.py
Requer: pip install markdown; Chromium (variável CHROME ou caminho padrão do ambiente).
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "pdf"
CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

CSS = """
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
body { font-family: "DejaVu Sans", "Liberation Sans", Arial, sans-serif; font-size: 12.5pt;
       line-height: 1.5; color: #1a1a1a; }
h1 { font-size: 21pt; color: #0b3d6b; border-bottom: 3px solid #0b3d6b; padding-bottom: 4px; }
h2 { font-size: 16pt; color: #0b3d6b; margin-top: 26px; border-bottom: 1px solid #c9d6e3;
     padding-bottom: 2px; page-break-after: avoid; }
h3 { font-size: 13.5pt; color: #174f86; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 11pt;
        page-break-inside: auto; }
th, td { border: 1px solid #b8c4d0; padding: 5px 7px; vertical-align: top; text-align: left; }
th { background: #e8eef5; }
tr { page-break-inside: avoid; }
blockquote { margin: 12px 0; padding: 8px 12px; background: #f4f7fb;
             border-left: 4px solid #3b78b5; }
blockquote p { margin: 4px 0; }
code { background: #f0f0f0; padding: 1px 4px; border-radius: 3px; font-size: 10.5pt; }
pre { background: #f6f6f6; padding: 10px; border: 1px solid #ddd; white-space: pre-wrap;
      font-size: 10.5pt; }
hr { border: none; border-top: 1px solid #ccd; margin: 20px 0; }
a { color: #174f86; }
li { margin: 2px 0; }
.rodape { font-size: 9pt; color: #777; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 6px; }
"""

LISTA = re.compile(r"^(\s*)([-*+]|\d+\.)\s")


def preparar(md: str) -> str:
    """Ajusta o Markdown às regras do Python-Markdown (linha em branco antes de listas,
    recuo de 4 espaços em sublistas) e converte caixas de seleção."""
    saida = []
    anterior = ""
    for linha in md.split("\n"):
        prefixo = ""
        corpo = linha
        m = re.match(r"^((?:>\s?)+)(.*)$", linha)
        if m:
            prefixo, corpo = m.group(1), m.group(2)
        # sublistas com 2 espaços -> 4 espaços
        ml = re.match(r"^( +)([-*+]|\d+\.)\s", corpo)
        if ml:
            nivel = len(ml.group(1)) // 2
            corpo = "    " * nivel + corpo.lstrip(" ")
        corpo = re.sub(r"^(\s*[-*+]) \[ \] ", r"\1 ☐ ", corpo)
        corpo = re.sub(r"^(\s*[-*+]) \[x\] ", r"\1 ☑ ", corpo)
        ant_corpo = re.sub(r"^(?:>\s?)+", "", anterior)
        if LISTA.match(corpo) and ant_corpo.strip() and not LISTA.match(ant_corpo) \
                and not ant_corpo.startswith("    "):
            saida.append(prefixo.rstrip())
        saida.append(prefixo + corpo)
        anterior = prefixo + corpo
    return "\n".join(saida)


def links_para_pdf(html: str) -> str:
    # links relativos entre documentos .md passam a apontar para o PDF correspondente
    return re.sub(r'href="(?!https?:)([^"#]*/)?([^"/#]+)\.md(#[^"]*)?"',
                  lambda m: f'href="{m.group(2)}.pdf"', html)


def converter(arquivo: Path) -> Path:
    texto = preparar(arquivo.read_text(encoding="utf-8"))
    corpo = markdown.markdown(texto, extensions=["tables", "fenced_code", "sane_lists"])
    corpo = links_para_pdf(corpo)
    titulo = arquivo.stem
    html = (f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
            f"<title>{titulo}</title><style>{CSS}</style></head><body>{corpo}"
            f"<div class='rodape'>PRF ADM 2026 · {arquivo.relative_to(RAIZ)}</div></body></html>")
    SAIDA.mkdir(exist_ok=True)
    destino = SAIDA / f"{titulo}.pdf"
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
        tmp.write(html)
    subprocess.run([CHROME, "--headless", "--no-sandbox", "--disable-gpu",
                    "--no-pdf-header-footer", f"--print-to-pdf={destino}",
                    f"file://{tmp.name}"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.unlink(tmp.name)
    return destino


def main() -> None:
    arquivos = sorted((RAIZ / "docs").glob("*.md")) + sorted((RAIZ / "docs" / "apostila").glob("*.md"))
    if len(sys.argv) > 1:
        arquivos = [Path(a).resolve() for a in sys.argv[1:]]
    for arq in arquivos:
        print("PDF:", converter(arq).relative_to(RAIZ))


if __name__ == "__main__":
    main()
