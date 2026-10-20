# SPDX-License-Identifier: GPL-2.0-or-later

"""Fase 2 (Opción A): Sistema de Transformación.

W/E/R transforman al instante con los operadores nativos (modo inmediato) o
seleccionan los tools nativos (gizmo). En el 3D View, W y E pasan por
`modoz.w_move` / `modoz.e_rotate` para restringir el movimiento a los dos
ejes que miran a la vista y la rotación al eje de profundidad, en el espacio
de la orientación de transformación activa (ver view_transform.py).
"""

from . import view_transform
from . import tools


def register():
    view_transform.register()
    tools.register()


def unregister():
    tools.unregister()
    view_transform.unregister()
