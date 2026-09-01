"""Validação do 7º cenário (cooperative_door_bypass).

Verifica:
  1. reset() não rebenta e cria a geometria esperada (2 segmentos + defletor + porta).
  2. A PORTA FUNCIONA: abre quando >=3 agentes estão na push zone.
  3. Existe um bypass navegável com a porta fechada, e é geodesicamente MAIS LONGO
     que o caminho pela porta (cooperar = melhor).

Corre-se à mão:  python scripts/test_cenario_bypass.py

O nome começa por `test_`, por isso o `pytest` sem argumentos apanha-o. O
corpo está dentro de `main()` de propósito: enquanto esteve ao nível do módulo,
importá-lo executava-o — e um `pytest` na raiz do repositório morria na
recolha, sem chegar a correr um único teste da suite (dois erros: este ficheiro
e a cópia dele em `out/pi/`). É também a razão de o `sys.exit` só acontecer
quando este ficheiro é o programa.
"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import yaml
from src.environment.swarm_env_3d import SwarmForagingEnv3D

OK, FAIL = "[OK]", "[FALHA]"


def main():
    falhas = 0

    with open(os.path.join(os.path.dirname(__file__), "../configs/foraging.yaml")) as f:
        cfg = yaml.safe_load(f)
    cfg["environment"]["classic_scenario"] = "cooperative_door_bypass"
    cfg["environment"]["num_agents"] = 20

    env = SwarmForagingEnv3D(config=cfg)
    obs, _ = env.reset(seed=42)

    # 1) Geometria
    print("=== 1. Geometria ===")
    print(f"  nº paredes: {len(env.walls)} (esperado 4: esq + dir + defletor + porta)")
    if len(env.walls) != 4:
        falhas += 1; print(f"  {FAIL} nº de paredes inesperado")
    else:
        print(f"  {OK} 4 paredes")
    print(f"  door_active={env.door_active}, door_wall_index={env.door_wall_index}, door_pos={env.door_pos}")
    print(f"  obs shape={obs['robot_0'].shape}")

    # 2) A PORTA FUNCIONA
    print("\n=== 2. Mecânica da porta (push zone: x in (-1.5,1.5), y in (-2,0)) ===")
    # Teste 2a: 2 agentes na push zone -> porta NAO abre
    env.reset(seed=42)
    env.agent_positions[0] = np.array([-0.8, -1.0, 0.0])
    env.agent_positions[1] = np.array([ 0.8, -1.0, 0.0])
    # afastar os restantes para longe da push zone
    for k in range(2, env.num_agents):
        env.agent_positions[k] = np.array([-12.0, -12.0, 0.0])
    acoes = {a: np.zeros(3, dtype=np.float32) for a in env.agents}
    env.step(acoes)
    if env.door_active:
        print(f"  {OK} com 2 agentes a porta mantém-se FECHADA (door_active=True)")
    else:
        falhas += 1; print(f"  {FAIL} porta abriu com apenas 2 agentes")

    # Teste 2b: 3 agentes na push zone -> porta ABRE
    env.reset(seed=42)
    paredes_fechada = len(env.walls)
    env.agent_positions[0] = np.array([-1.0, -1.0, 0.0])
    env.agent_positions[1] = np.array([ 0.0, -1.0, 0.0])
    env.agent_positions[2] = np.array([ 1.0, -1.0, 0.0])
    for k in range(3, env.num_agents):
        env.agent_positions[k] = np.array([-12.0, -12.0, 0.0])
    env.step(acoes)
    # Abrir = REMOVER o painel de env.walls (ver _update_door). Isto verificava
    # a semântica ANTIGA — o painel afastado para uma posição > 900 — e, desde
    # que a porta passou a ser removida, `door_wall_index` volta a None e a
    # verificação rebentava com TypeError em vez de falhar com uma mensagem.
    porta_abriu = (not env.door_active
                   and env.door_wall_index is None
                   and len(env.walls) == paredes_fechada - 1)
    if porta_abriu:
        print(f"  {OK} com 3 agentes a porta ABRE (door_active=False, painel removido: "
              f"{paredes_fechada} -> {len(env.walls)} paredes)")
    else:
        falhas += 1
        print(f"  {FAIL} porta NÃO abriu com 3 agentes (door_active={env.door_active}, "
              f"door_wall_index={env.door_wall_index}, paredes={len(env.walls)})")

    # 3) Bypass navegável e mais longo que a porta
    print("\n=== 3. Geodésico: porta (curto) vs bypass (longo) ===")
    spawn = np.array([0.0, -8.0, 0.0])   # sul, alinhado com a porta

    def dist_geodesica(env, porta_bloqueada):
        """Recalcula o campo geodésico; se porta_bloqueada, trata a porta como parede."""
        env._geo_cache = {}
        saved = env.door_wall_index
        if porta_bloqueada:
            env.door_wall_index = -999  # nenhum índice => porta não é saltada => bloqueada
        env._build_geodesic_field()
        env.door_wall_index = saved
        i, j = env._to_cell(spawn)
        d = env.geo_field[i, j]
        return float(d)

    env.reset(seed=42)
    d_porta  = dist_geodesica(env, porta_bloqueada=False)  # caminho curto pela porta
    d_bypass = dist_geodesica(env, porta_bloqueada=True)   # caminho longo sem porta
    print(f"  dist. spawn->ninho pela PORTA  : {d_porta:.2f} m")
    print(f"  dist. spawn->ninho pelo BYPASS : {d_bypass:.2f} m")

    if not np.isfinite(d_porta):
        falhas += 1; print(f"  {FAIL} caminho pela porta inalcançável")
    elif not np.isfinite(d_bypass):
        falhas += 1; print(f"  {FAIL} bypass INALCANÇÁVEL com porta fechada (cenário ficaria sem saída!)")
    elif d_bypass <= d_porta:
        falhas += 1; print(f"  {FAIL} bypass não é mais longo ({d_bypass:.1f} <= {d_porta:.1f})")
    else:
        print(f"  {OK} bypass navegável e {d_bypass/d_porta:.1f}x mais longo que a porta")

    # Resumo
    print("\n" + ("=" * 40))
    if falhas == 0:
        print(">>> TODOS OS TESTES PASSARAM")
    else:
        print(f">>> {falhas} TESTE(S) FALHARAM")
    return falhas


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
