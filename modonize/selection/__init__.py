# SPDX-License-Identifier: GPL-2.0-or-later

"""Paquete del sistema de selección de Modonize."""

from . import mode_memory
from . import operator_cycle
from . import double_click
from . import handlers


def register():
    handlers.register()
    operator_cycle.register()
    double_click.register()


def unregister():
    handlers.unregister()
    double_click.unregister()
    operator_cycle.unregister()