# -*- coding: utf-8 -*-
"""Testes das melhorias do evo_trainer_3d (12 jul 2026, pré-mega-treino).

Contrato testado:
1. _update_novelty_weight (novelty adaptativo):
   - novelty_adaptive=False → w intacto;
   - streak de comida interrompida reinicia a contagem (sem anneal);
   - após novelty_sustain_gens gerações consecutivas com comida entra em anneal
     e decai ×novelty_decay/chamada; abaixo de 1e-3 fecha em 0.0 EXATO e o
     método passa a no-op (seleção volta ao objetivo puro).
2. Cache da fitness dos elites (elite_cache):
   - treino com cache ON é BIT-EXACTO ao treino com cache OFF (mesma seed,
     mesmo config) nas colunas best_fitness/avg_fitness/best_task_food,
     geração a geração — com e sem Novelty Search ativo.
   - (timestep/time diferem por construção: os elites cacheados não executam
     passos de ambiente.)
3. CSV por run: gnn_3d_training{suf}_run{seed}.csv existe e tem as mesmas
   linhas que o CSV canónico gnn_3d_training.csv.

Uso: .venv/Scripts/python.exe tests/test_evo_melhorias.py
(Os treinos usam um config miniatura em dir temporário; nada em results/ é tocado.)
"""
import csv
import os
import sys
import tempfile
from types import SimpleNamespace

import yaml

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.training.evo_trainer_3d import GeneticTrainer3D

CONFIG = os.path.join(os.path.dirname(__file__), "..", "configs", "foraging.yaml")

FALHAS = []


def check(cond, msg):
    """Regista e imprime. NÃO falha sozinho — ver a nota no fim do ficheiro.

    Cada função de teste tem de terminar com `_exigir()`, senão as verificações
    correm e o pytest dá o teste por passado aconteça o que acontecer.
    """
    tag = "[ok]" if cond else "[FALHA]"
    print(f"  {tag} {msg}")
    if not cond:
        FALHAS.append(msg)


def _exigir():
    """Converte o que o `check` acumulou numa falha de teste, e limpa.

    Sem isto — e foi assim até 5 ago — o `test_anneal_unit` corria as suas oito
    verificações do anneal adaptativo e passava sempre no pytest, porque não
    tinha uma única asserção: o `check` só imprime. Oito verificações do
    mecanismo central da QI6 (a dosagem adaptativa da novidade) a dar verde
    incondicional, e a suite a contá-las como cobertura.
    """
    global FALHAS
    pendentes, FALHAS = list(FALHAS), []
    assert not pendentes, "verificações falhadas:\n  - " + "\n  - ".join(pendentes)


# 1. unit: anneal
def _dummy(w=0.5, adaptive=True, decay=0.5, sustain=3):
    return SimpleNamespace(novelty_weight=w, novelty_adaptive=adaptive,
                           novelty_decay=decay, novelty_sustain_gens=sustain,
                           _food_streak=0, _novelty_annealing=False)


def test_anneal_unit():
    print("[1] _update_novelty_weight (unit)")
    upd = GeneticTrainer3D._update_novelty_weight

    d = _dummy(adaptive=False)
    for _ in range(20):
        upd(d, best_food=5.0)
    check(d.novelty_weight == 0.5, "adaptive=False: w intacto após 20 gens com comida")

    d = _dummy()
    for food in [1, 1, 0, 1, 1, 0, 1, 1]:   # nunca 3 seguidas
        upd(d, best_food=food)
    check(d.novelty_weight == 0.5 and not d._novelty_annealing,
          "streak interrompida: sem anneal, w intacto")

    d = _dummy()
    upd(d, 1.0); upd(d, 1.0)
    check(d.novelty_weight == 0.5, "2/3 da streak: ainda sem decair")
    upd(d, 1.0)   # 3ª consecutiva → arma o anneal (decai a partir da PRÓXIMA)
    check(d._novelty_annealing and d.novelty_weight == 0.5,
          "streak completa arma o anneal sem decair já")
    upd(d, 1.0)
    check(abs(d.novelty_weight - 0.25) < 1e-12, "anneal: w decai ×decay por chamada")
    upd(d, 0.0)   # comida a zero não trava o anneal (não re-arma)
    check(abs(d.novelty_weight - 0.125) < 1e-12, "anneal continua mesmo com food=0")
    for _ in range(10):
        upd(d, 1.0)
    check(d.novelty_weight == 0.0, "abaixo de 1e-3 fecha em 0.0 exato")
    upd(d, 1.0)
    check(d.novelty_weight == 0.0, "com w=0.0 o método é no-op")
    _exigir()


# 2/3. treinos miniatura (Pool)
def _mini_config(tmpdir, novelty_weight, novelty_adaptive, elite_cache):
    with open(CONFIG, "r") as f:
        cfg = yaml.safe_load(f)
    cfg["environment"].update({"num_agents": 5, "max_steps": 60,
                               "classic_scenario": "none", "num_obstacles": 10})
    cfg["simulation"]["max_steps"] = 60
    cfg["evolution"].update({"pop_size": 8, "eval_episodes": 2,
                             "novelty_weight": novelty_weight,
                             "novelty_adaptive": novelty_adaptive,
                             "novelty_sustain_gens": 3,
                             "elite_cache": elite_cache})
    path = os.path.join(tmpdir, f"cfg_nov{novelty_weight}_cache{elite_cache}.yaml")
    with open(path, "w") as f:
        yaml.safe_dump(cfg, f)
    return path


def _run_mini(tmpdir, tag, novelty_weight, novelty_adaptive, elite_cache,
              minutos=0.5, seed=5):
    cfg = _mini_config(tmpdir, novelty_weight, novelty_adaptive, elite_cache)
    log_dir = os.path.join(tmpdir, f"logs_{tag}")
    model_dir = os.path.join(tmpdir, f"models_{tag}")
    trainer = GeneticTrainer3D(cfg, time_limit_minutes=minutos, seed=seed,
                               log_dir=log_dir, model_dir=model_dir)
    trainer.train()
    per_run = os.path.join(log_dir, f"gnn_3d_training_run{seed}.csv")
    canon = os.path.join(log_dir, "gnn_3d_training.csv")
    return canon, per_run


def _le_csv(path):
    with open(path, newline="") as f:
        return list(csv.reader(f))


def _cache_equivalencia(tmpdir, novelty_weight, novelty_adaptive, rotulo):
    # Nome com `_` à frente, como os outros auxiliares deste ficheiro: chamava-se
    # `test_...` e o pytest tentava tratá-lo como teste, pedindo os argumentos
    # como fixtures ("fixture 'novelty_weight' not found"). Continua a ser
    # chamado do __main__ com os parâmetros explícitos, que é como foi escrito.
    print(f"[2] equivalência elite_cache ON vs OFF ({rotulo})")
    canon_off, per_off = _run_mini(tmpdir, f"{rotulo}_off", novelty_weight,
                                   novelty_adaptive, elite_cache=False)
    canon_on, per_on = _run_mini(tmpdir, f"{rotulo}_on", novelty_weight,
                                 novelty_adaptive, elite_cache=True)

    rows_off, rows_on = _le_csv(per_off)[1:], _le_csv(per_on)[1:]
    n = min(len(rows_off), len(rows_on))
    check(n >= 3, f"gerações comuns suficientes (off={len(rows_off)}, on={len(rows_on)})")
    # colunas: timestep, best_fitness, avg_fitness, best_task_food, time
    difs = [g for g in range(n) if rows_off[g][1:4] != rows_on[g][1:4]]
    check(not difs, f"fitness/média/comida bit-exactas nas {n} gerações comuns"
                    + (f" (1ª divergência: gen {difs[0]+1})" if difs else ""))

    print("[3] CSV por run = CSV canónico")
    check(_le_csv(canon_on) == _le_csv(per_on),
          "linhas do canónico == linhas do por-run (cache ON)")
    _exigir()


# As partes 2 e 3 só corriam no `__main__` — ou seja, nunca no pytest, e a suite
# dava-as por cobertas. São dois treinos miniatura de 30 s cada por braço; o
# preço é ~2 min, e o que compram é a garantia de que o cache de elites não muda
# um único número (é o que autoriza tê-lo ligado nas campanhas).
import pytest  # noqa: E402


@pytest.mark.parametrize("w,adapt,rotulo", [
    (0.0, False, "objetivo"),
    (0.5, True, "novelty_adapt"),
])
def test_cache_de_elites_nao_muda_resultados(tmp_path, w, adapt, rotulo):
    _cache_equivalencia(str(tmp_path), novelty_weight=w,
                        novelty_adaptive=adapt, rotulo=rotulo)


if __name__ == "__main__":
    test_anneal_unit()
    with tempfile.TemporaryDirectory() as tmpdir:
        _cache_equivalencia(tmpdir, novelty_weight=0.0,
                                novelty_adaptive=False, rotulo="objetivo")
        _cache_equivalencia(tmpdir, novelty_weight=0.5,
                                novelty_adaptive=True, rotulo="novelty_adapt")
    print()
    if FALHAS:
        print(f"[RESULTADO] {len(FALHAS)} falha(s):")
        for f in FALHAS:
            print(f"  - {f}")
        sys.exit(1)
    print("[RESULTADO] todos os testes passaram")
