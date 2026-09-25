# SPDX-License-Identifier: GPL-2.0-or-later

"""Fase 3: Editor. Atajos de edición (selección up/down, bevel, loops,
subdividir) y tecla F de foco."""

from . import mesh_ops
from . import mesh_shortcuts
from . import focus


def register():
    mesh_ops.register()
    mesh_shortcuts.register()
    focus.register()


def unregister():
    focus.unregister()
    mesh_shortcuts.unregister()
    mesh_ops.unregister()