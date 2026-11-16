# -*- coding: utf-8 -*-
"""Genera notebooks/proyecto_final_neveras.ipynb a partir de nb_parts/*.py"""
import json, pathlib, glob

ns = {}
exec(open('nb_parts/p00_header.py', encoding='utf-8').read(), ns)
for f in sorted(glob.glob('nb_parts/p[0-9]*.py')):
    if f.endswith('p00_header.py'): continue
    exec(open(f, encoding='utf-8').read(), ns)
    print(f'  + {f}')

CELLS = ns['CELLS']
nb = {"cells": CELLS,
      "metadata": {"colab": {"provenance": [], "toc_visible": True},
                   "kernelspec": {"display_name": "Python 3", "name": "python3"},
                   "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
pathlib.Path('notebooks').mkdir(exist_ok=True)
out = pathlib.Path('notebooks/proyecto_final_neveras.ipynb')
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
n_md = sum(1 for c in CELLS if c['cell_type'] == 'markdown')
print(f'\n{out}: {len(CELLS)} celdas ({n_md} markdown, {len(CELLS)-n_md} codigo)')
