"""Genera lenguajes.svg con los lenguajes más usados en todos los repos propios.

Suma los bytes por lenguaje que reporta la API de GitHub en cada repositorio
del dueño del token (privados incluidos, sin forks ni archivados) y dibuja la
tarjeta con el mismo tema y alto que la de rachas (tokyonight, 195 px).
"""

import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

API = "https://api.github.com"
MAX_LENGUAJES = 6
EXCLUIR_REPOS = {"GustavoQuinteroC"}
SALIDA = sys.argv[1] if len(sys.argv) > 1 else "lenguajes.svg"

COLORES = {
    "PHP": "#4F5D95", "CSS": "#663399", "HTML": "#e34c26", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "Python": "#3572A5", "C++": "#f34b7d", "C": "#555555",
    "Shell": "#89e051", "Hack": "#878787", "Blade": "#f7523f", "SCSS": "#c6538c",
    "Vue": "#41b883", "Dockerfile": "#384d54", "Java": "#b07219", "Go": "#00ADD8",
    "PLpgSQL": "#336790", "TSQL": "#e38c00", "Jupyter Notebook": "#DA5B0B",
}


def pedir(url, token):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def contar(token):
    totales, pagina = {}, 1
    while True:
        repos = pedir(f"{API}/user/repos?affiliation=owner&per_page=100&page={pagina}", token)
        if not repos:
            return totales
        for repo in repos:
            if repo["fork"] or repo["archived"] or repo["name"] in EXCLUIR_REPOS:
                continue
            for lenguaje, bytes_ in pedir(repo["languages_url"], token).items():
                totales[lenguaje] = totales.get(lenguaje, 0) + bytes_
        pagina += 1


def dibujar(totales):
    total = sum(totales.values())
    top = sorted(totales.items(), key=lambda x: -x[1])[:MAX_LENGUAJES]
    porcentajes = [(n, 100 * b / total) for n, b in top]

    barra, x = [], 0.0
    suma_top = sum(p for _, p in porcentajes)
    for nombre, p in porcentajes:
        ancho = 300 * p / suma_top
        barra.append(f'<rect x="{x:.2f}" width="{ancho:.2f}" height="10" fill="{COLORES.get(nombre, "#8b949e")}"/>')
        x += ancho

    leyenda = []
    for i, (nombre, p) in enumerate(porcentajes):
        col, fila = (25, i) if i < 3 else (185, i - 3)
        y = 105 + fila * 25
        leyenda.append(
            f'<circle cx="{col + 5}" cy="{y - 4}" r="5" fill="{COLORES.get(nombre, "#8b949e")}"/>'
            f'<text x="{col + 16}" y="{y}" class="lang">{escape(nombre)} {p:.2f}%</text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="350" height="195" viewBox="0 0 350 195" role="img" aria-labelledby="titulo">
  <title id="titulo">Lenguajes más usados</title>
  <style>
    .titulo {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #70a5fd; }}
    .lang {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #38bdae; }}
  </style>
  <rect width="350" height="195" fill="#1a1b27"/>
  <text x="25" y="40" class="titulo">Lenguajes más usados</text>
  <svg x="25" y="62" width="300" height="10">
    <mask id="barra"><rect width="300" height="10" rx="5" fill="#fff"/></mask>
    <g mask="url(#barra)">
      {"".join(barra)}
    </g>
  </svg>
  {"".join(leyenda)}
</svg>
"""


if __name__ == "__main__":
    token = os.environ.get("LENGUAJES_TOKEN")
    if not token:
        sys.exit("Falta el secret LENGUAJES_TOKEN")
    totales = contar(token)
    if not totales:
        sys.exit("La API no regresó lenguajes; se deja la tarjeta anterior")
    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write(dibujar(totales))
    print("Lenguajes:", ", ".join(f"{n} {b}" for n, b in sorted(totales.items(), key=lambda x: -x[1])))
