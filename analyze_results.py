import pandas as pd
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, 'results', 'graficos_tese', 'estatisticas', 'all_best_scores.csv')

if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    
    # 1. Agrupar por Cenario e Algoritmo para ver Médias e Desvio Padrão
    resumo = df.groupby(['Scenario', 'Algorithm'])['BestScore'].agg(['mean', 'std', 'max', 'min']).round(2)
    print("--- RESUMO DO DESEMPENHO (BEST SCORES) ---")
    print(resumo)
    
    # 2. Encontrar eventuais runs que falharam (score muito baixo)
    # Assumindo que score abaixo de 0 é um falhanço total
    falhas = df[df['BestScore'] < 0]
    if not falhas.empty:
        print("\n--- AVISO: RUNS QUE FALHARAM REDONDAMENTE (<0) ---")
        print(falhas)
    else:
        print("\n✅ Todas as runs terminaram com score positivo (sem falhas totais na aprendizagem).")
else:
    print(f"Ficheiro {csv_path} não encontrado!")
