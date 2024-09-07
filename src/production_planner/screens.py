# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .core import CONFIG

import os
from pathlib import Path
from typing import Iterable

from textual import on
from textual.containers import Grid
from textual.screen import Screen, ModalScreen
from textual.app import ComposeResult
from textual.widgets import DirectoryTree, Label, Button, Footer, Input, Pretty
from textual.validation import Function


def filtered_directory_tree(show_files=True, show_directories=True, **init_kwargs):
    class FilteredDirectoryTree(DirectoryTree):
        def __init__(*args, **inner_kwargs):
            return DirectoryTree.__init__(*args, **(inner_kwargs | init_kwargs))

        def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
            def filt(entry):
                if not show_files and entry.is_file():
                    return False
                elif not show_directories and entry.is_dir():
                    return False

                is_hidden = entry.name.startswith(".")
                is_datafile = entry.suffix == ".yaml"
                return (not is_hidden) and (is_datafile or entry.is_dir())
            return [path for path in paths if filt(path)]

    return FilteredDirectoryTree


class DataFileAction(Screen[str]):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    data = []
    expand_all = False
    FirstDTree = None
    entry = False
    SecondDTree = None

    def compose(self) -> ComposeResult:
        self.first_dtree = self.FirstDTree(CONFIG.dpath_data)
        if self.SecondDTree:
            self.second_dtree = self.SecondDTree(CONFIG.dpath_data)

        if self.entry:
            def has_dot(value: str) -> bool:
                return "." not in value
            yield Pretty([])
            yield Input(placeholder="file name", validators=[Function(has_dot, "Don't add file extension manually"), ])

        yield self.first_dtree
        if self.SecondDTree:
            self.second_dtree = self.SecondDTree(CONFIG.dpath_data)
            yield self.second_dtree
        yield Footer()

    @property
    def highlighted_path(self) -> Path:
        current = self.first_dtree.cursor_node
        return None if current is None else current.data.path

    def on_mount(self) -> None:
        # All these lines to simply move the cursor to the currently open file/folder
        prev_path = Path(CONFIG.store["last_file"])
        if self.entry:
            self.query_one(Input).value = os.path.splitext(str(prev_path))[0]

        tree = self.first_dtree
        node_current = tree.root
        with tree.prevent(tree.FileSelected):
            if self.expand_all:
                tree.expand_all()

            for name in prev_path.parts:
                for node in node_current.children:
                    if name == node.label.plain:
                        node_current = node
                        node_current.expand()
                        # FIXME: Expanding a node will asynchronously load the contained files and folders.
                        #        That leads to not being able to move the cursor to those nodes since `children` is not populated yet.
                        #        I'm not quite sure how to block until all that lazy loading is finished and integrated into the tree.
                        #
                        #        Perhaps one quick fix would be to manually build the substructure without relying on `node.expand`...
                else:
                    break
            tree.move_cursor(node_current)

    @on(Input.Changed)
    def show_invalid_reasons(self, event: Input.Changed) -> None:
        # Updating the UI to show the reasons why validation failed
        if not event.validation_result.is_valid:  # (4)!
            self.query_one(Pretty).update(event.validation_result.failure_descriptions)
        else:
            self.query_one(Pretty).update([])

    def on_input_submitted(self, event: Input.Submitted):
        if event.validation_result.is_valid:
            fname = Path(event.value + ".yaml")
            subdir = self.highlighted_path

            fpath = CONFIG.dpath_data.parent / subdir / fname
            if fpath.is_file():
                def handle_overwrite(overwrite: bool):
                    if overwrite:
                        self.dismiss(fpath)

                self.app.push_screen(OverwriteScreen(), handle_overwrite)
            else:
                self.dismiss(fpath)

    def on_tree_node_highlighted(self, node):
        path = self.highlighted_path
        if self.SecondDTree and path.is_dir():
            self.second_dtree.path = path
            self.second_dtree.reload()

    def on_directory_tree_file_selected(self, selected: DirectoryTree.FileSelected):
        self.dismiss(selected.path)

    def action_cancel(self):
        self.dismiss("")


# TODO: add some way to delete directories
class SelectDataFile(DataFileAction):
    entry = False
    FirstDTree = filtered_directory_tree(show_files=True)


# TODO: add some way to create directories (though implicitly possible by typing the relative path in the entry widget)
class SaveDataFile(DataFileAction):
    entry = True
    FirstDTree = filtered_directory_tree(show_files=False)
    SecondDTree = filtered_directory_tree(show_files=True, show_directories=False, disabled=True)


class OverwriteScreen(ModalScreen[bool]):  # (1)!
    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Do you want to overwrite the existing file?", id="question"),
            Button("Yes", variant="warning", id="overwrite"),
            Button("No", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "overwrite":
            self.dismiss(True)
        else:
            self.dismiss(False)
