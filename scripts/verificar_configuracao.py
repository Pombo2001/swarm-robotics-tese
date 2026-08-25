#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""As tabelas de configuração descrevem o simulador que produziu os resultados?

    python scripts/verificar_configuracao.py
    python scripts/verificar_configuracao.py --listar   # o que cada tabela diz

Porque existe
-------------
O Apêndice tem duas tabelas — `tab:apx_env` (a física e a recompensa) e
`tab:apx_train` (os hiperparâmetros dos três algoritmos) — que dizem, parâmetro
a parâmetro, com que sistema foram produzidos os resultados da dissertação. São
cerca de 45 valores, e nenhum verificador olhava para eles.

É a mesma classe de defeito que este projeto já teve com as figuras: a tabela é
uma **cópia** do `configs/foraging.yaml` feita à mão num certo dia. O YAML muda
— e mudou muitas vezes: o LiDAR de 5 para 8 m, a recompensa simplificada em
junho, o `max_steps` do mapa composto, o `required_to_eat` por cenário — e a
tabela fica a descrever um simulador que já não existe. Ninguém dá por isso a
reler, porque a tabela continua coerente consigo mesma.

Um valor errado aqui é pior do que um resultado errado: um resultado errado
contradiz um CSV, mas uma configuração errada faz o leitor pensar que reproduziu
o trabalho quando correu outra coisa.

⚠️ O que esta régua NÃO faz: não julga o que o valor devia ser. Compara o que a
tese escreve com o que o ficheiro declara, e diz onde diferem.
"""
import argparse
import os
import re
import sys

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(RAIZ, "Tese", "main.tex")
CFG = os.path.join(RAIZ, "configs", "foraging.yaml")

# Onde vive cada parâmetro dentro do YAML. A tabela do ambiente mistura duas
# secções do ficheiro (a física e a recompensa vivem ambas em `environment`), e
# os hiperparâmetros de treino vivem um por algoritmo.
SECCOES = {"env": ["environment"], "ppo": ["ppo"], "sac": ["sac"], "ae": ["evolution"]}

# Parâmetros que a tabela declara e o YAML não tem com o mesmo nome — cada um
# com a razão. Declarar é parte do resultado: o que não se confere aqui não
# desaparece, fica com o motivo à frente.
SEM_CHAVE = {}

# Os parâmetros da procura por novidade não estão no YAML: o `evo_trainer_3d`
# lê-os do `evo_config` com valor por omissão, e as campanhas de Novelty passam
# o `w` por linha de comandos. A fonte deles é, portanto, o CÓDIGO — e é lá que
# se vai buscá-los, em vez de os declarar isentos.
DO_CODIGO = os.path.join(RAIZ, "src", "training", "evo_trainer_3d.py")


def valor_tex(bruto):
    """«$500\\,000$», «$10^{-4}$», «$0{,}02$\\,m/s» → número."""
    s = bruto.strip()
    exp = re.search(r"10\^\{(-?\d+)\}", s)
    if exp:
        return float(10.0 ** int(exp.group(1)))
    s = re.sub(r"\\,|\\;|\\ ", "", s)                    # separador de milhares
    s = re.sub(r"\\text[a-z]*\{[^}]*\}|\\[a-zA-Z]+", " ", s)
    s = s.replace("$", "").replace("{,}", ".").replace("+", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group(0)) if m else None


def linhas_da_tabela(tex, label):
    """As linhas «\\texttt{chave} & valor & …» de uma tabela, pelo seu rótulo."""
    i = tex.find("\\label{%s}" % label)
    if i < 0:
        return []
    fim = tex.find("\\end{tabular}", i)
    saida = []
    # A tabela dos hiperparâmetros só nomeia o algoritmo na PRIMEIRA linha de
    # cada bloco; as seguintes abrem com «&». O algoritmo corrente arrasta-se
    # de linha para linha, e é ele que decide em que secção do YAML procurar.
    algoritmo = None
    for linha in tex[i:fim].split("\\\\"):
        alg = re.search(r"\\textbf\{(PPO|SAC|Evolutivo)", linha)
        if alg:
            algoritmo = {"PPO": "ppo", "SAC": "sac", "Evolutivo": "evolution"}[alg.group(1)]
        m = re.search(r"\\texttt\{([^}]+)\}", linha)
        if not m:
            continue
        chave = m.group(1).replace("\\_", "_")
        # O valor é a célula a seguir à do nome — e o nome nem sempre está na
        # primeira: a tabela dos hiperparâmetros abre com o algoritmo
        # («\textbf{PPO} & \texttt{learning_rate} & $10^{-4}$»). Tomar a
        # coluna 2 lia o nome do parâmetro como se fosse o valor dele, e as 22
        # linhas dessa tabela saíam todas como «valor não numérico».
        celulas = [c.strip() for c in linha.split("&")]
        i_nome = next((i for i, c in enumerate(celulas) if "\\texttt{" in c), 0)
        if i_nome + 1 >= len(celulas):
            continue
        saida.append((chave, celulas[i_nome + 1], " ".join(linha.split())[:90],
                      algoritmo))
    return saida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listar", action="store_true")
    args = ap.parse_args()

    linhas = open(TEX, encoding="utf-8").read().split("\n")
    tex = "\n".join(l for l in linhas if not l.lstrip().startswith("%"))
    cfg = yaml.safe_load(open(CFG, encoding="utf-8"))

    print("=" * 78)
    print("CONFIGURAÇÃO: as tabelas do Apêndice  vs  configs/foraging.yaml")
    print("=" * 78)

    falhas, conferidos, isentos = [], 0, []

    def do_codigo(chave):
        """O valor por omissão que o treinador evolutivo usa, lido do código."""
        fonte = open(DO_CODIGO, encoding="utf-8").read()
        m = re.search(r"evo_config\.get\(['\"]%s['\"],\s*([\d.]+)\)" % re.escape(chave),
                      fonte)
        return (float(m.group(1)), "evo_trainer_3d.py") if m else (None, None)

    def procurar(chave, algoritmo=None):
        """O valor no YAML, procurado nas secções onde ele pode viver.

        Com `algoritmo`, a secção desse algoritmo tem precedência: o `net_arch`
        e o `num_cpu` existem no `ppo` E no `sac`, e sem esta precedência as
        linhas do SAC eram conferidas contra os valores do PPO — passavam por
        acaso, porque hoje são iguais, e deixariam de o fazer no dia em que um
        deles mudasse.
        """
        if algoritmo:
            bloco = cfg.get(algoritmo) or {}
            if isinstance(bloco, dict) and chave in bloco:
                return bloco[chave], algoritmo
        # O YAML tem dez secções e a tabela não as distingue: o `agent_radius`
        # vive em `physics`, o `food_collected` em `rewards`, o `hidden_dim` em
        # `gnn_agent` e o `guillotine_threshold` em `simulation`. Procurar só em
        # quatro dava sete «não existe» que existiam todas.
        for seccao, bloco in cfg.items():
            if isinstance(bloco, dict) and chave in bloco:
                return bloco[chave], seccao
        if chave in cfg:
            return cfg[chave], "(raiz)"
        return None, None

    for label in ("tab:apx_env", "tab:apx_train"):
        print("\n  %s" % label)
        entradas = linhas_da_tabela(tex, label)
        if not entradas:
            falhas.append("não encontrei a tabela %s no main.tex" % label)
            continue
        for chave, bruto, contexto, algoritmo in entradas:
            base = chave.split()[0]
            se_yaml, seccao = procurar(base, algoritmo)
            if se_yaml is None:
                se_yaml, seccao = do_codigo(base)
            if se_yaml is None:
                razao = SEM_CHAVE.get(base)
                isentos.append((base, razao or "não existe no YAML com este nome"))
                if razao is None:
                    falhas.append("%s: a tabela declara «%s» e o YAML não tem "
                                  "essa chave" % (label, base))
                continue
            na_tese = valor_tex(bruto)
            if na_tese is None:
                isentos.append((base, "valor não numérico na tabela: %s" % bruto.strip()))
                continue
            if isinstance(se_yaml, (list, tuple, dict, str)):
                # `net_arch: [256, 256]` é uma lista, e comparar listas com
                # números é outra pergunta. Confere-se que a tabela nomeia as
                # mesmas dimensões, e diz-se que é isso que se confere.
                dims = re.findall(r"\d+", str(bruto))
                iguais = [str(x) for x in se_yaml] == dims if isinstance(
                    se_yaml, (list, tuple)) else str(se_yaml) == bruto.strip()
                print("    [%s] %-38s tese %-12s yaml %s (%s)"
                      % ("v" if iguais else "!", base, ",".join(dims), se_yaml, seccao))
                conferidos += 1
                if not iguais:
                    falhas.append("%s: a tese diz %s e o YAML diz %s"
                                  % (base, dims, se_yaml))
                continue
            conferidos += 1
            ok = abs(float(se_yaml) - na_tese) <= max(1e-9, abs(float(se_yaml)) * 1e-6)
            print("    [%s] %-38s tese %-12s yaml %s (%s)"
                  % ("v" if ok else "!", base, na_tese, se_yaml, seccao))
            if not ok:
                falhas.append("%s: a tese diz %s e o %s diz %s"
                              % (base, na_tese, os.path.basename(CFG), se_yaml))
        if args.listar:
            for chave, bruto, contexto, _alg in entradas:
                print("      · %s" % contexto)

    if isentos:
        print("\n  Não conferidos, com razão declarada:")
        for chave, razao in isentos:
            print("    %-38s %s" % (chave, razao))

    print("\n" + "=" * 78)
    if falhas:
        print("%d divergência(s) entre a tese e a configuração:" % len(falhas))
        for f in falhas:
            print("  - %s" % f)
        print("=" * 78)
        sys.exit(1)
    print("Os %d valores das tabelas de configuração batem com o foraging.yaml ✓"
          % conferidos)
    print("=" * 78)


if __name__ == "__main__":
    main()
