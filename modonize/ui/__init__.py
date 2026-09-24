# SPDX-License-Identifier: GPL-2.0-or-later

"""UI del addon Modonize."""

from . import panel


def register():
    panel.register()


def unregister():
    panel.unregister()