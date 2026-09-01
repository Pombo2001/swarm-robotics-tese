"""Configuração do pytest para os testes do projeto.

Os testes deste projeto são scripts autónomos: correm com
`.venv/Scripts/python.exe tests/test_x.py` e fazem o seu trabalho no corpo do
módulo. Todos expõem também funções `test_*`, por isso `pytest tests/` corre a
suite inteira.

Histórico (para não se repetir): `test_dashboard_jobs.py` corria tudo à
importação e acabava em `sys.exit(0)`; durante a *coleção* isso subia como
INTERNALERROR e abortava a corrida toda — nem um teste dos outros ficheiros
corria. A 25 jul o ficheiro foi excluído aqui (`collect_ignore`), o que devolveu
o `pytest tests/` mas deixou o mecanismo do dashboard sem cobertura na suite. A
27 jul foi convertido para funções `test_*`, com o `sys.exit` só no bloco
`__main__`, e a exclusão deixou de fazer falta.

Regra: um teste novo nunca chama `sys.exit()` (nem faz trabalho pesado) no
corpo do módulo — só dentro de funções `test_*` ou do `if __name__ == "__main__"`.
"""
