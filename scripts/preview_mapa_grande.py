"""
preview_mapa_grande.py — RETIRADO (a geometria vive no simulador)
================================================================
Este ficheiro era o RASCUNHO do mapa grande: a geometria vivia aqui enquanto se
decidia TAMANHO e ASPETO (plantas a r=30/45/60, ninho e 20 robôs à escala, pior
percurso por BFS). O docstring original dizia que a geometria ficava aqui "até o
mapa ser aprovado" e que depois passaria a `_spawn_obstacles_mapa_grande` em
`src/environment/swarm_env_3d.py`. Isso aconteceu a 24 jul 2026.

**Porque foi retirado e não corrigido:** ficou a ser uma SEGUNDA cópia da
geometria, e as duas divergiram em silêncio. Quando as zonas A e B foram
corrigidas no simulador (beco em U espelhado, quatro salas a sério), este
ficheiro continuou a desenhar o mapa antigo — e é um script que produz figuras
para a tese e para a defesa. Manter duas implementações da mesma geometria é a
armadilha que já fez o 7.º cenário ser treinado e nunca avaliado.

A decisão que este rascunho existia para apoiar está **congelada**: r=60,
103×62 m, 5 zonas (ver `docs/PRE_REGISTO_MAPA_GRANDE.md`). Não há mais nada a
pré-visualizar antes de existir.

O que usar em vez disto — tudo lê a geometria do AMBIENTE REAL:

  planta 2D para a tese      scripts/gerar_figuras_mapa_grande.py
  vista 3D (Ursina)          visualization/visualize_mapa_grande.py
  auditoria da topologia     tests/test_mapa_grande.py

O conteúdo original está no git: `git show 22922fb:scripts/preview_mapa_grande.py`.
"""
import sys

MENSAGEM = (__doc__ or "").strip()

if __name__ == "__main__":
    print(MENSAGEM)
    sys.exit(2)
