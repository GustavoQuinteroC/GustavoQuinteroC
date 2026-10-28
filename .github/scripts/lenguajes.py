"""Genera lenguajes.svg con los lenguajes más usados en todos los repos propios.

Cuenta en cuántos repositorios del dueño del token (privados incluidos, sin
forks ni archivados) aparece cada lenguaje con al menos MIN_PARTICIPACION de
ese repo. Se cuenta por repositorio y no por bytes para que un proyecto chico
en otro lenguaje pese lo mismo que uno grande. Dibuja la tarjeta con el mismo
tema y alto que la de rachas (tokyonight, 195 px) y acomoda hasta
MAX_LENGUAJES en dos columnas.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

API = "https://api.github.com"
MAX_LENGUAJES = 12
# Un lenguaje cuenta para un repo si ocupa al menos esta parte de su código;
# así el CSS o JS de una librería incluida no suma el repo entero.
MIN_PARTICIPACION = 0.10
EXCLUIR_REPOS = {"GustavoQuinteroC"}
SALIDA = sys.argv[1] if len(sys.argv) > 1 else "lenguajes.svg"

COLORES = {
    "PHP": "#4F5D95", "CSS": "#663399", "HTML": "#e34c26", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "Python": "#3572A5", "C++": "#f34b7d", "C": "#555555",
    "Shell": "#89e051", "Hack": "#878787", "Blade": "#f7523f", "SCSS": "#c6538c",
    "Vue": "#41b883", "Dockerfile": "#384d54", "Java": "#b07219", "Go": "#00ADD8",
    "PLpgSQL": "#336790", "TSQL": "#e38c00", "Jupyter Notebook": "#DA5B0B",
}


VENCE = {}


def pedir(url, token):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            # Ejemplo: "2027-10-27 06:00:00 UTC"
            if r.headers.get("github-authentication-token-expiration"):
                VENCE["fecha"] = r.headers["github-authentication-token-expiration"]
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 401:
            sys.exit("El token LENGUAJES_TOKEN venció o ya no es válido. Genera uno nuevo "
                     "(solo lectura de metadatos, todos los repositorios) y reemplaza el secret.")
        raise


def avisar_vencimiento():
    """Deja en GITHUB_OUTPUT los días que le quedan al token."""
    if "fecha" not in VENCE:
        return
    vence = datetime.strptime(VENCE["fecha"].replace(" UTC", ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    dias = (vence - datetime.now(timezone.utc)).days
    print(f"El token vence el {vence:%Y-%m-%d} ({dias} días)")
    salida = os.environ.get("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write(f"dias_token={dias}\nvence_token={vence:%Y-%m-%d}\n")


def contar(token):
    """Regresa {lenguaje: [repos, bytes]}."""
    totales, pagina = {}, 1
    while True:
        repos = pedir(f"{API}/user/repos?affiliation=owner&per_page=100&page={pagina}", token)
        if not repos:
            return totales
        for repo in repos:
            if repo["fork"] or repo["archived"] or repo["name"] in EXCLUIR_REPOS:
                continue
            lenguajes = pedir(repo["languages_url"], token)
            total_repo = sum(lenguajes.values())
            for lenguaje, bytes_ in lenguajes.items():
                if bytes_ / total_repo < MIN_PARTICIPACION:
                    continue
                dato = totales.setdefault(lenguaje, [0, 0])
                dato[0] += 1
                dato[1] += bytes_
        pagina += 1


def dibujar(totales):
    # Más repos primero; a igual número de repos, más código primero.
    top = sorted(totales.items(), key=lambda x: (-x[1][0], -x[1][1]))[:MAX_LENGUAJES]
    suma_repos = sum(r for _, (r, _) in top)

    barra, x = [], 0.0
    for nombre, (repos, _) in top:
        ancho = 300 * repos / suma_repos
        barra.append(f'<rect x="{x:.2f}" width="{ancho:.2f}" height="10" fill="{COLORES.get(nombre, "#8b949e")}"/>')
        x += ancho

    # Dos columnas; el espacio entre renglones y la letra se ajustan a la
    # cantidad para que la tarjeta no pase de 195 px.
    filas = max(3, -(-len(top) // 2))
    primera, ultima = 100, 178
    paso = min(25, (ultima - primera) / (filas - 1))
    letra = {3: 13, 4: 13, 5: 12}.get(filas, 11)
    radio = 5 if filas <= 4 else 4

    leyenda = []
    for i, (nombre, (repos, _)) in enumerate(top):
        col, fila = (25, i) if i < filas else (185, i - filas)
        y = primera + 4 + fila * paso
        texto = f"{repos} repo" if repos == 1 else f"{repos} repos"
        leyenda.append(
            f'<circle cx="{col + 5}" cy="{y - 4:.1f}" r="{radio}" fill="{COLORES.get(nombre, "#8b949e")}"/>'
            f'<text x="{col + 16}" y="{y:.1f}" class="lang">{escape(nombre)} <tspan class="num">{texto}</tspan></text>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="350" height="195" viewBox="0 0 350 195" role="img" aria-labelledby="titulo">
  <title id="titulo">Lenguajes más usados</title>
  <style>
    .titulo {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #70a5fd; }}
    .lang {{ font: 400 {letra}px 'Segoe UI', Ubuntu, Sans-Serif; fill: #38bdae; }}
    .num {{ fill: #a9b1d6; }}
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
    print("Lenguajes:", ", ".join(f"{n} {r} repos/{b} bytes" for n, (r, b) in sorted(totales.items(), key=lambda x: (-x[1][0], -x[1][1]))))
    avisar_vencimiento()
