"""Pacote do dashboard 'Mission Control' (NiceGUI).

Migração incremental do antigo launcher_dashboard.py (CustomTkinter). Os scripts em
scripts/ continuam a ser o backend; este pacote apenas orquestra.
"""


def _calar_timers_ao_fechar_a_pagina():
    """Fechar o separador enchia a consola de tracebacks que não são avarias.

    Um `ui.timer` do NiceGUI vai buscar o `parent_slot` em dois sítios, e os
    dois rebentam quando a página fechou entretanto:

      1. à ENTRADA (`_get_context`), antes de o ciclo do timer começar — o
         timer espera pela ligação do cliente e, se ela morreu à espera, o slot
         já não existe;
      2. na SAÍDA (`_cleanup`), onde o timer se remove do slot — dentro de um
         `finally`, ou seja depois de o próprio NiceGUI já ter (e bem) decidido
         não chamar o callback.

    Em nenhum dos dois há guarda possível do lado do callback: os `try/except`
    que os timers do `curvas.py` e do `app.py` já tinham nunca chegavam a ser
    executados. Cada timer vivo dava assim um traceback ao fechar a página —
    e as animações de contagem davam mais uma dúzia (essas deixaram de ser
    timers, ver `theme.js_diferido`).

    Aqui engole-se só este caso: sem slot não há contexto para entrar nem de
    onde sair. O `_should_stop()` do NiceGUI continua a travar o callback, e
    qualquer outro erro continua a subir.
    """
    from contextlib import nullcontext

    from nicegui.elements.timer import Timer

    _contexto, _limpeza = Timer._get_context, Timer._cleanup

    def _get_context_silencioso(self):
        try:
            return _contexto(self)
        except RuntimeError as e:
            if "deleted" not in str(e):
                raise
            return nullcontext()

    def _cleanup_silencioso(self):
        try:
            _limpeza(self)
        except RuntimeError as e:
            if "deleted" not in str(e):
                raise
            self.callback = None        # o que o cleanup da classe base faz

    Timer._get_context = _get_context_silencioso
    Timer._cleanup = _cleanup_silencioso


_calar_timers_ao_fechar_a_pagina()
