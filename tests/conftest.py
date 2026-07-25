"""Configuração do pytest para os testes do projeto.

Os testes deste projeto são **scripts autónomos**: correm com
`.venv/Scripts/python.exe tests/test_x.py` e fazem o seu trabalho no corpo do
módulo. A maioria também funciona com `pytest` porque expõe funções `test_*`.

`test_dashboard_jobs.py` não: corre tudo à importação (lança processos reais) e
acaba em `sys.exit(0)`. Durante a *coleção*, esse `sys.exit` sobe como
`INTERNALERROR` e **aborta a corrida inteira** — `pytest tests/` não corria um
único teste dos outros ficheiros, incluindo os do mapa. Ignorá-lo aqui devolve o
`pytest tests/` a quem o quiser usar; ele continua a correr como script, que é
como foi escrito.
"""

collect_ignore = ["test_dashboard_jobs.py"]
