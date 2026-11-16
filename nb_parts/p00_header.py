# -*- coding: utf-8 -*-
CELLS = []

def _lineas(s):
    'Convierte texto en la lista de lineas que exige el formato .ipynb (con \\n al final).'
    txt = s.strip('\n')
    partes = txt.split('\n')
    return [p + '\n' for p in partes[:-1]] + [partes[-1]]

def md(s):
    CELLS.append({"cell_type": "markdown", "metadata": {}, "source": _lineas(s)})

def code(s):
    CELLS.append({"cell_type": "code", "execution_count": None, "metadata": {},
                  "outputs": [], "source": _lineas(s)})
