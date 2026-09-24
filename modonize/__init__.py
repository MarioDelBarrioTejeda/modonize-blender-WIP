# SPDX-License-Identifier: GPL-2.0-or-later

bl_info = {
    "name": "Modonize Blender",
    "author": "Modonize",
    "version": (0, 1, 0),
    "blender": (4, 5, 0),
    "location": "3D View > Edit Mode",
    "description": (
        "Porta parte de la experiencia de modelado de Luxology Modo a Blender. "
        "Primer entregable: sistema de selección en Edit Mode."
    ),
    "category": "Mesh",
}

# Modo de ejecución en estructura de paquete: los submodules importan el
# estado compartido (caché de memoria de selección) y se registran aquí.

from . import preferences
from . import keymaps
from . import selection
from . import ui

modules = (
    preferences,
    keymaps,
    selection,
    ui,
)


def register():
    for mod in modules:
        mod.register()


def unregister():
    # Se invierte el orden para desregistrar de forma limpia (los keymaps
    # dependen de los operadores, así que se limpian los keymaps primero).
    for mod in reversed(modules):
        mod.unregister()