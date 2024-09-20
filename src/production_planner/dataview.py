#! /bin/env python
# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from io import StringIO
from difflib import unified_diff

from textual.screen import Screen
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    TextArea,
    Label,
    Footer,
)
from textual.app import ComposeResult

import yaml


class YamlEditor(TextArea):
    ...


class DiffEditor(TextArea):
    ...


class DataView(Screen):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    CSS_PATH = "DataView.tcss"

    def __init__(self, table, *args, **kwargs):
        self.table = table
        super().__init__(*args, **kwargs)

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical():
                yield Label("File in session")
                # FIXME: when `editor.read_only == False` then the `escape` > `action_cancel` binding doesn't work anymore
                new = yaml.dump(self.table.nodetree)
                yield YamlEditor.code_editor(new, language="yaml", read_only=True)

            with Vertical():
                old = yaml.dump(self.table.sink.sink._data)
                diff = StringIO()
                diff.writelines(unified_diff(old.splitlines(keepends=True),
                                             new.splitlines(keepends=True),
                                             fromfile="sink.yaml",
                                             tofile="staging.yaml"))
                yield Label("Difference to saved file")
                yield DiffEditor.code_editor(diff.getvalue(), language="yaml", read_only=True)
        yield Footer()

    def action_cancel(self):
        self.dismiss("")
