# Travessias de paredes — modelos arquivados

Gerado por `scripts/detetar_travessias.py` (3 episódios determinísticos por modelo).
Um modelo **atravessa** se um agente entrou numa parede por um lado e saiu pelo oposto; «pelo teto» quando entrou a menos de 1 m do teto da esfera. Um modelo está **preso** se teve agentes dentro de paredes sem nunca as atravessar (junções em T). Modelos idênticos em várias pastas contam uma vez.

## Por cenário e algoritmo (todas as campanhas, modelos únicos)

| cenário | algo | modelos | atravessam | dos quais pelo teto | só presos | z máx |
|---|---|---|---|---|---|---|
| four_rooms | GNN | 16 | 8 **⚠** | 3 | 3 | 14.8 |
| u_wall | GNN | 117 | 2 **⚠** | 0 | 8 | 14.6 |
| cooperative_door_bypass | GNN | 77 | 1 **⚠** | 0 | 0 | 12.7 |
| bottleneck | GNN | 16 | 0 | 0 | 0 | 4.5 |
| bottleneck | PPO | 1 | 0 | 0 | 0 | 1.6 |
| bottleneck | SAC | 1 | 0 | 0 | 0 | 13.1 |
| cooperative_door | GNN | 16 | 0 | 0 | 0 | 5.3 |
| cooperative_door | PPO | 1 | 0 | 0 | 0 | 4.5 |
| cooperative_door | SAC | 1 | 0 | 0 | 0 | 4.0 |
| cooperative_door_bypass | PPO | 1 | 0 | 0 | 0 | 2.4 |
| cooperative_door_bypass | SAC | 1 | 0 | 0 | 0 | 2.1 |
| cooperative_perception | GNN | 34 | 0 | 0 | 0 | 11.7 |
| cooperative_perception | PPO | 1 | 0 | 0 | 0 | 10.3 |
| cooperative_perception | SAC | 1 | 0 | 0 | 0 | 10.2 |
| four_rooms | PPO | 1 | 0 | 0 | 0 | 14.6 |
| four_rooms | SAC | 1 | 0 | 0 | 0 | 14.4 |
| mapa_grande | GNN | 22 | 0 | 0 | 0 | 2.0 |
| none | GNN | 31 | 0 | 0 | 0 | 14.1 |
| none | PPO | 1 | 0 | 0 | 0 | 11.5 |
| none | SAC | 1 | 0 | 0 | 0 | 11.5 |
| u_wall | PPO | 1 | 0 | 0 | 0 | 3.7 |
| u_wall | SAC | 1 | 0 | 0 | 1 | 3.0 |

## Modelos que atravessam

| cenário | algo | campanha(s) | run | travessias | pelo teto | z máx | rec/ep |
|---|---|---|---|---|---|---|---|
| cooperative_door_bypass | GNN | mega_B5/mega_B7 | 4 | 1 | 0 | 5.6 | 77.3 |
| four_rooms | GNN | adaptativo_A1/adaptativo_A2/mega_A1/mega_A2/mega_A5 | 2 | 48 | 0 | 4.3 | 55.3 |
| four_rooms | GNN | adaptativo_A1/adaptativo_A2/mega_A1/mega_A2/mega_A5 | 3 | 56 | 0 | 2.0 | 71.7 |
| four_rooms | GNN | adaptativo_A1/adaptativo_A2/mega_A1/mega_A2/mega_A5 | 4 | 37 | 0 | 4.0 | 56.0 |
| four_rooms | GNN | adaptativo_A1/adaptativo_A2/mega_A1/mega_A2/mega_A5 | 5 | 67 | 67 | 14.8 | 77.3 |
| four_rooms | GNN | adaptativo_A1/adaptativo_A2/mega_A1/mega_A2/mega_A5 | campeão | 67 | 67 | 14.8 | 77.3 |
| four_rooms | GNN | final_7d | 1 | 61 | 0 | 2.5 | 61.3 |
| four_rooms | GNN | final_7d | 4 | 65 | 65 | 14.8 | 63.3 |
| four_rooms | GNN | final_7d | 6 | 3 | 0 | 14.8 | 42.3 |
| u_wall | GNN | mega_A1 | 1 | 6 | 0 | 1.4 | 54.7 |
| u_wall | GNN | mega_A2/mega_A5 | 13 | 1 | 0 | 7.3 | 52.0 |

**343 modelos únicos (771 ficheiros): 11 atravessam paredes (3 deles pelo teto), 12 só ficam presos em junções.**
