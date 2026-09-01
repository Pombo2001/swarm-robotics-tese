# -*- coding: utf-8 -*-
"""Confere os números da PRIMEIRA PARTE da tese (caps. 1-4) contra as fontes.

O `verificar_numeros_tese.py` cobre os RESULTADOS (tabelas e prosa do cap. 6)
contra os CSV das campanhas. Não cobre o que vem antes: a geometria dos cenários,
os hiperparâmetros, as dimensões do espaço de observação, os números da revisão
sistemática. Esses vivem no `configs/foraging.yaml`, no `src/` e no
`docs/slr/screening.csv` — e podem divergir do texto sem que nada acuse.

Uso:  .venv/Scripts/python.exe scripts/verificar_parte1.py
"""
import csv
import os
import re
import sys

import yaml

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.append(RAIZ)

TEX = os.path.join(RAIZ, "Tese", "main.tex")
CFG = os.path.join(RAIZ, "configs", "foraging.yaml")
SCREENING = os.path.join(RAIZ, "docs", "slr", "screening.csv")

_okays, _falhas = [], []


def confere(rotulo, no_texto, na_fonte, fonte):
    igual = str(no_texto) == str(na_fonte)
    (_okays if igual else _falhas).append(
        (rotulo, no_texto, na_fonte, fonte, igual))


def _tex():
    with open(TEX, encoding="utf-8") as f:
        return f.read()


def _num(texto, padrao, grupo=1):
    """Extrai um número do .tex, normalizando a vírgula decimal do LaTeX."""
    m = re.search(padrao, texto)
    if not m:
        return None
    return m.group(grupo).replace("{,}", ".").replace(",", ".")


def main():
    tex = _tex()
    with open(CFG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    env = cfg["environment"]

    # Ambiente: o que o cap. 4 afirma vs configs/foraging.yaml
    confere("nº de agentes (N)",
            _num(tex, r"\$N\s*=\s*(\d+)\$ agentes"), env["num_agents"], "foraging.yaml")
    confere("raio da arena",
            _num(tex, r"r_\{arena\}\s*=\s*(\d+)"),
            int(env["arena_radius"]), "foraging.yaml")

    # Dimensão da observação: a tese afirma R^111 em vários sítios.
    from src.environment.swarm_env_3d import SwarmForagingEnv3D
    e = SwarmForagingEnv3D(CFG)
    obs_dim = int(e.observation_space_val.shape[0])
    confere("dimensão da observação",
            _num(tex, r"\\mathbb\{R\}\^\{(\d+)\}"), obs_dim, "swarm_env_3d")
    # A ação aparece no texto como o triplo (a_F, a_R, a_U): conta-se pelos
    # componentes declarados, não por um expoente que o texto não escreve.
    m = re.search(r"\\mathbf\{a\}_i = \(([^)]*)\)", tex)
    confere("dimensão da ação",
            len(m.group(1).split(",")) if m else None,
            int(e.action_space_val.shape[0]), "swarm_env_3d")

    # Tabela de hiperparâmetros do apêndice, linha a linha
    # É a tabela mais frágil da dissertação: cada linha é um valor do YAML
    # copiado à mão, e o YAML muda entre campanhas. Lê-se do .tex por regex
    # (\texttt{chave} & $valor$) e compara-se com a chave correspondente.
    achatado = {}
    for seccao, dic in cfg.items():
        if isinstance(dic, dict):
            for k, v in dic.items():
                achatado.setdefault(k, (v, seccao))
    # A chave pode vir seguida do símbolo matemático — `\texttt{pop\_size} ($K$) & $30$`
    # — por isso aceita-se qualquer coisa curta entre a chave e o `&`.
    linha = re.compile(r"\\texttt\{([a-z_0-9\\]+)\}[^&\n]{0,30}&\s*\$?([+-]?[0-9][0-9{},.^\\ ]*)")
    vistos = 0
    for m in linha.finditer(tex):
        chave = m.group(1).replace("\\_", "_")
        if chave not in achatado:
            continue
        bruto = m.group(2)
        # 500{,}000 -> 500000 ; 0{,}015 -> 0.015 ; 10^{-4} fica de fora (potência).
        txt = bruto.replace("\\,", "").replace("$", "").strip()
        if "^" in txt:
            continue
        # Separador de MILHARES só quando a parte inteira não é "0": sem esta
        # condição, `0{,}015` (quinze milésimos) era lido como "0015" = 15.
        milhares = re.fullmatch(r"([1-9][0-9]{0,2})(\{,\}[0-9]{3})+", txt)
        txt = txt.replace("{,}", "") if milhares else txt.replace("{,}", ".")
        try:
            no_texto = float(txt.rstrip("."))
        except ValueError:
            continue
        valor, seccao = achatado[chave]
        if not isinstance(valor, (int, float)):
            continue
        vistos += 1
        confere(f"{chave}", no_texto, float(valor), f"foraging.yaml:{seccao}")
    print(f"[i] tabela de hiperparâmetros: {vistos} linhas com par no YAML")

    # Revisão sistemática: os números do PRISMA vêm do screening.csv
    if os.path.exists(SCREENING):
        with open(SCREENING, encoding="utf-8") as f:
            linhas = list(csv.DictReader(f))
        incluidos = sum(1 for r in linhas if r.get("decisao") == "incluir")
        confere("estudos incluídos (SLR)",
                _num(tex, r"corpo da revis[ãa]o \(\$n=(\d+)\$\)"),
                incluidos, "screening.csv")

    # Relatório
    print("=" * 72)
    print("PARTE 1 (caps. 1-4) — texto vs configuração e código")
    print("=" * 72)
    for rot, t, f, fonte, _ in _okays:
        print(f"  ok   {rot:<28} {t} = {f}   ({fonte})")
    for rot, t, f, fonte, _ in _falhas:
        print(f"  ERRO {rot:<28} tese diz {t!r}, fonte diz {f!r}   ({fonte})")
    print("-" * 72)
    print(f"{len(_okays)} conferidos, {len(_falhas)} divergentes")
    return 1 if _falhas else 0


if __name__ == "__main__":
    sys.exit(main())
