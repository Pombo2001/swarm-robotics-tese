#!/usr/bin/env python3
"""Empacota o dashboard para correr noutra máquina (o Raspberry Pi 5), em modo leitura.

Porquê um empacotador e não um `git clone`
------------------------------------------
O repositório com os resultados tem **1,4 GB**, e a maior parte é peso morto para
quem só quer VER: 586 MB de modelos `.zip` (stable-baselines), 265 MB de GIFs e
os `.pth` do evolutivo. O orientador não vai treinar nada — precisa das figuras,
dos CSV que as sustentam e do texto da tese que a vista Defesa lê.

O que VAI (medido a 31 jul):
    · código do dashboard + src/ + scripts/ + configs/          ~4 MB
    · CSV e PNG de todas as campanhas (inclui as exploratórias,
      para se ver a evolução do projeto)                        ~285 MB
    · GIFs de todas as campanhas que os têm                    ~265 MB
    · results/{evaluation,estatisticas,heatmaps,mapa_grande}    ~11 MB
    · os .tex da tese e do artigo (a vista Defesa lê o main.tex)  <1 MB

O que NÃO vai: modelos (.pth/.zip), logs de treino em cru, PDFs, .git.

Sem modelos, o dashboard **não precisa de torch nem de stable-baselines** —
verificado: nenhuma vista os importa. No Pi bastam nicegui, pandas, plotly,
numpy e pyyaml.

Uso:
    python scripts/empacotar_para_pi.py                 # cria out/pi/ e o .tar.gz
    python scripts/empacotar_para_pi.py --sem-videos    # menos 35 MB
    python scripts/empacotar_para_pi.py --so-canonicas  # só as campanhas da tese
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import sys
import tarfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DESTINO = os.path.join(RAIZ, "out", "pi")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Pastas de código copiadas por inteiro (menos o lixo de execução).
CODIGO = ["dashboard", "src", "scripts", "configs", "docs"]
IGNORAR_CODIGO = shutil.ignore_patterns("__pycache__", "*.pyc", "*.log", ".pytest_cache")

# Ficheiros de dados: extensões que o dashboard lê.
EXT_DADOS = (".csv", ".json", ".yaml", ".yml", ".md", ".txt")
EXT_FIGURAS = (".png",)
EXT_VIDEOS = (".gif",)

# Pastas de results a levar (as de modelos ficam de fora por serem inúteis aqui).
RESULTS_DADOS = ["evaluation", "estatisticas", "heatmaps", "mapa_grande",
                 "novelty_adaptativo", "mega_1mes", "logs"]

CANONICAS = ("final_7d", "adaptativo_", "mega_", "estatisticas", "eval_7d")


def _copiar(orig: str, dest: str) -> int:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(orig, dest)
    return os.path.getsize(orig)


def empacotar(sem_videos: bool, so_canonicas: bool) -> None:
    if os.path.isdir(DESTINO):
        shutil.rmtree(DESTINO)
    os.makedirs(DESTINO)
    total = 0

    print("[1/5] código")
    for pasta in CODIGO:
        o = os.path.join(RAIZ, pasta)
        if os.path.isdir(o):
            shutil.copytree(o, os.path.join(DESTINO, pasta), ignore=IGNORAR_CODIGO)
    total += sum(os.path.getsize(os.path.join(r, f))
                 for p in CODIGO for r, _, fs in os.walk(os.path.join(DESTINO, p)) for f in fs)

    print("[2/5] campanhas (figuras + CSV)")
    base = os.path.join(RAIZ, "results", "graficos_tese")
    n_camp = n_fig = 0
    for camp in sorted(os.listdir(base)):
        o = os.path.join(base, camp)
        if not os.path.isdir(o) or camp.startswith("_"):
            continue
        if so_canonicas and not camp.startswith(CANONICAS):
            continue
        n_camp += 1
        for raiz_dir, _, ficheiros in os.walk(o):
            # `videos/` é a única subpasta que interessa, e só na campanha da tese.
            e_video = os.path.basename(raiz_dir) == "videos"
            for f in ficheiros:
                ext = os.path.splitext(f)[1].lower()
                if e_video:
                    # TODOS os GIFs, não só os da campanha da tese. A restrição
                    # poupava 230 MB, mas deixava o Pi com 16 campanhas com vídeo
                    # contra 22 na torre — e a diferença não era explicável a
                    # quem lá fosse ver. Em LAN, 230 MB são 30 segundos.
                    if sem_videos or ext not in EXT_VIDEOS:
                        continue
                elif ext not in EXT_DADOS + EXT_FIGURAS:
                    continue
                rel = os.path.relpath(os.path.join(raiz_dir, f), RAIZ)
                total += _copiar(os.path.join(raiz_dir, f), os.path.join(DESTINO, rel))
                n_fig += 1
    print(f"      {n_camp} campanhas, {n_fig} ficheiros")

    print("[3/5] dados de results/")
    for sub in RESULTS_DADOS:
        o = os.path.join(RAIZ, "results", sub)
        if not os.path.isdir(o):
            continue
        for raiz_dir, _, ficheiros in os.walk(o):
            for f in ficheiros:
                if os.path.splitext(f)[1].lower() not in EXT_DADOS + EXT_FIGURAS:
                    continue
                rel = os.path.relpath(os.path.join(raiz_dir, f), RAIZ)
                total += _copiar(os.path.join(raiz_dir, f), os.path.join(DESTINO, rel))

    print("[4/5] texto da tese e do artigo (a vista Defesa lê o main.tex)")
    for rel in ["Tese/main.tex", "Tese/apendice_slr.tex", "Artigo/artigo.tex"]:
        o = os.path.join(RAIZ, rel)
        if os.path.exists(o):
            total += _copiar(o, os.path.join(DESTINO, rel))
    # A vista Mapa serve a planta a partir de Tese/images/resultados.
    fig_tese = os.path.join(RAIZ, "Tese", "images", "resultados")
    if os.path.isdir(fig_tese):
        for f in os.listdir(fig_tese):
            if f.endswith(".png"):
                total += _copiar(os.path.join(fig_tese, f),
                                 os.path.join(DESTINO, "Tese", "images", "resultados", f))

    # Instruções mínimas ao lado do pacote — quem o abrir daqui a um mês não tem
    # de reconstruir isto de cabeça.
    with open(os.path.join(DESTINO, "LEIA-ME-PI.md"), "w", encoding="utf-8") as f:
        f.write(LEIAME)

    print("[5/5] tar.gz")
    tar = os.path.join(RAIZ, "out", "dashboard_pi.tar.gz")
    with tarfile.open(tar, "w:gz") as t:
        # O nome de topo do tar é o da pasta no Pi: extrai-se com
        # --strip-components=1 -C ~/TeseRobotics e fica tudo no sítio.
        t.add(DESTINO, arcname="TeseRobotics")
    print(f"\n[v] {DESTINO}  ({total/1048576:.0f} MB)")
    print(f"[v] {tar}  ({os.path.getsize(tar)/1048576:.0f} MB comprimido)")
    print("\nNo Pi:  tar xzf dashboard_pi.tar.gz -C ~/          "
          "# fica em ~/TeseRobotics")
    print("        cd ~/TeseRobotics && SWARM_DASH_READONLY=1 PORT=8090 "
          "python3 -m dashboard.app")


LEIAME = """# Dashboard da tese — cópia de leitura (Raspberry Pi)

Gerado por `scripts/empacotar_para_pi.py`. **Modo leitura**: sem Treinar, sem
Ao vivo (3D) e sem o painel do servidor — este último pede a password SSH do
ISCTE, que não tem lugar num site publicado.

## Instalar

    sudo apt install python3-venv
    python3 -m venv .venv && . .venv/bin/activate
    pip install nicegui pandas plotly numpy pyyaml

Não é preciso torch nem stable-baselines: sem modelos, nenhuma vista os importa.

## Correr

    SWARM_DASH_READONLY=1 PORT=8090 python3 -m dashboard.app

A porta 8090 está livre neste Pi (80/443/81 são do Nginx Proxy Manager, 3000 é o
Homepage, 3001 é o dizquesim, 8080/8081/8096/9001/9443 estão ocupados).

## Serviço (arranca com o Pi)

    /etc/systemd/system/swarm-dash.service

    [Unit]
    Description=Swarm Observatory (dashboard da tese, leitura)
    After=network.target

    [Service]
    User=pi5
    WorkingDirectory=/home/pi5/TeseRobotics
    Environment=SWARM_DASH_READONLY=1
    Environment=PORT=8090
    ExecStart=/home/pi5/TeseRobotics/.venv/bin/python -m dashboard.app
    Restart=always

    [Install]
    WantedBy=multi-user.target

    sudo systemctl daemon-reload && sudo systemctl enable --now swarm-dash

## HTTPS + password (Nginx Proxy Manager)

1. Criar o subdomínio no DuckDNS (a mesma conta do site) a apontar para o IP de casa.
2. No NPM (http://<pi>:81): Proxy Host -> o subdomínio -> `127.0.0.1:8090`,
   **Websockets Support LIGADO** (o NiceGUI vive de websockets; sem isto a página
   abre e fica parada).
3. SSL -> pedir certificado Let's Encrypt, Force SSL.
4. **Access List** com utilizador/password, e associá-la ao Proxy Host. São dados
   de uma tese ainda não submetida: não devem ficar abertos nem indexáveis.

## Atualizar

Gerar o pacote outra vez no PC e substituir a pasta. Os dados são só de leitura,
não há nada no Pi que se perca.
"""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sem-videos", action="store_true", help="não levar os GIFs (-35 MB)")
    p.add_argument("--so-canonicas", action="store_true",
                   help="só as campanhas da tese (sem as exploratórias)")
    a = p.parse_args()
    empacotar(a.sem_videos, a.so_canonicas)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
