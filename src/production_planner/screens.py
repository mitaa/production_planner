# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .core import CONFIG, DPATH_DATA, get_path, set_path, Ingredient, Producer, Purity, Recipe, PRODUCERS, PRODUCER_NAMES, PRODUCER_MAP, all_recipes_producer
from . import core
from . import datatable

import os
import re
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from typing import Iterable

from textual import on
from textual.containers import Grid
from textual.screen import Screen, ModalScreen
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import DataTable, DirectoryTree, Label, Button, Header, Footer, Input, Pretty, Select, SelectionList
from textual.widgets.selection_list import Selection
from textual.validation import Function
from textual.coordinate import Coordinate
from textual import events

from rich.text import Text


@dataclass
class SetCellValue:
    column: None
    value: None


class StringifyFilter:
    def __init__(self, search: str = ""):
        self._search = search

    @property
    def search(self):
        return self._search

    @search.setter
    def search(self, value: str):
        self._search = value
        self.words = value.split()

    def filter_item(self, item) -> bool:
        return all(word in str(item).lower() for word in self.words)


class FilteredListSelector(Screen[Producer]):
    CSS_PATH = "FilteredListSelector.tcss"
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    cell = None
    data = []
    data_sorted = []
    data_filtered = []
    data_filter = StringifyFilter()
    selected = None

    def on_mount(self) -> None:
        self.query_one(DataTable).cursor_type = "row"
        self.filt_input = self.query_one(Input)
        self.table = self.query_one(DataTable)
        self.sort()
        self.set_filt(None)
        self.query_one(DataTable).focus()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Horizontal(Input(placeholder="<text filter>"))
        yield DataTable()
        yield Footer()

    def sort(self):
        self.data_sorted = self.data

    @property
    def header(self):
        return self.query_one(Header)

    def action_cancel(self):
        self.app.sub_title = ""
        self.dismiss([])

    @on(Input.Submitted)
    def input_submitted(self, event: Input.Submitted):
        self.on_data_table_row_selected()

    def package(self) -> [SetCellValue]:
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        return [SetCellValue(self.cell, self.data_filtered[row])]

    def on_data_table_row_selected(self):
        if self.data_filtered:
            self.dismiss(self.package())
        else:
            self.dismiss([])

    @on(Input.Changed)
    def set_filt(self, event: Input.Changed) -> None:
        if event is None:
            self.data_filter.search = self.query_one(Input).value
        else:
            self.data_filter.search = event.value

        self.data_filtered = list(filter(self.data_filter.filter_item, self.data_sorted))
        self.update()
        self.select()

    def select(self):
        it_data = iter(self.data)
        table = self.query_one(DataTable)

        row_selected = None
        for row_number, filt_item in enumerate(self.data_filtered):
            for item in it_data:
                if item == self.selected:
                    row_selected = row_number
                    table.cursor_coordinate = Coordinate(row_selected or 0, 0)
                    return
                elif item == filt_item:
                    break

    def on_key(self, event: events.Key) -> None:
        if len(self.app.screen_stack) > 2:
            return

        match event.key:
            case "ctrl+up":
                self.filt_input.focus()
            case "up" | "down" if self.filt_input.has_focus:
                self.table.focus()
            case _ if len(event.key) == 1 and not self.filt_input.has_focus and event.key.isprintable():
                inp = self.query_one(Input)
                inp.focus()
                inp.value += event.key


class SelectProducer(FilteredListSelector):
    screen_title = "Producers"

    def on_mount(self) -> None:
        self.cell = datatable.ProducerCell
        self.data = PRODUCERS
        self.selected = self.app.selected_node.producer
        super().on_mount()

    def update(self):
        def bool_to_mark(a, mark="x"):
            return Text(mark if a else "", justify="center")
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("Building", "Power", "Miner", "Power Gen")
        rows = []
        for p in self.data_filtered:
            rows += [[Text(p.name),
                      Text(str(p.base_power), justify="right"),
                      bool_to_mark(p.is_miner),
                      bool_to_mark(p.is_pow_gen)]]
        table.add_rows(rows)


SELECT_PRODUCERS = [all_recipes_producer] + PRODUCERS


class RecipeFilterSetting(Enum):
    # Note: prompt == value in the SelectionList
    in_recipe_names = Selection(*["Recipe Names"] * 2, True)
    in_outputs = Selection(*["Outputs"] * 2, True)
    in_inputs  = Selection(*["Inputs"] * 2, False)
    # use_regex = Selection(*["Regex"] * 2, False)


class RecipeFilter(StringifyFilter):
    def __init__(self, search: str = "", *args, **kwargs):
        super().__init__(search, *args, **kwargs)
        self.use_regex = False
        self.search = search
        self.update_settings([m.value.prompt.plain for m in RecipeFilterSetting if m.value.initial_state])

    def update_settings(self, active_options: [str]):
        for member in RecipeFilterSetting:
            setattr(self, member.name, member.value.prompt.plain in active_options)

    @property
    def use_regex(self):
        return self._use_regex

    @use_regex.setter
    def use_regex(self, value):
        self._use_regex = value
        self.search = self.search

    @StringifyFilter.search.setter
    def search(self, value):
        self._search = value
        words = value.split()
        self.words = words
        try:
            re_search = re.compile(self.search, flags=re.IGNORECASE)
        except re.error:
            re_search = re.compile("")
            # Happens when for example value == "\\"

        def filt_regex(content: str):
            return re_search.search(content) is not None

        def filt_words(content: str):
            return all(word in content for word in words)

        self.filt = filt_regex if self.use_regex else filt_words

    def filter_item(self, item: Recipe) -> bool:
        def search_ingredients(ingredients: [Ingredient]) -> bool:
            for ingredient in ingredients:
                if self.filt(str(ingredient).lower()):
                    return True

        if self.in_recipe_names:
            if self.filt(item.name.lower()):
                return True

        if self.in_inputs:
            if search_ingredients(item.inputs):
                return True
        if self.in_outputs:
            if search_ingredients(item.outputs):
                return True


class SelectRecipe(FilteredListSelector):
    screen_title = "Recipes"
    data_filter = RecipeFilter()

    def on_mount(self) -> None:
        self.query_one(SelectionList).border_title = "[white]Look in:[/]"
        self.add_producer_column = False
        self.cell = datatable.RecipeCell
        if self.app.selected_node.is_module:
            self.app.selected_node.update_module_listings()

        self.data = self.app.selected_producer.recipes
        self.selected = self.app.selected_node.recipe
        super().on_mount()

    def compose(self) -> ComposeResult:
        # TODO: use the parent class's `compose` method and add the Select widget
        self.producer_listing = self._producer_listing(self.app.selected_producer.name)
        yield Header()
        yield Horizontal(
            Select([(producer, producer) for producer in self.producer_listing], allow_blank=False),
            Input(placeholder="<text filter>"),
            SelectionList(*[member.value for member in RecipeFilterSetting]),
        )
        yield DataTable()
        yield Footer()

    @on(SelectionList.SelectedChanged)
    def update_filter_settings(self, event: SelectionList.SelectedChanged):
        self.data_filter.update_settings(event.selection_list.selected)
        self.set_filt(None)

    def package(self) -> [SetCellValue]:
        producer = PRODUCER_MAP[self.query_one(Select).value]
        set_recipe: [SetCellValue] = super().package()
        # Note: keep the producer in front of the recipe - otherwise the `Node.recipe_cache` will be inconsistent
        return [SetCellValue(datatable.ProducerCell, set_recipe[0].value.producer)] + set_recipe

    def _producer_listing(self, producer_name):
        producer_list = [p.name for p in SELECT_PRODUCERS]
        del producer_list[producer_list.index(producer_name)]
        producer_list.insert(0, producer_name)
        return producer_list

    @on(Select.Changed)
    def relist_recipes(self, event: Select.Changed):
        # put the selected producer at the top
        self.producer_list = self._producer_listing(event.value)
        sel = self.query_one(Select)
        with sel.prevent(Select.Changed):
            sel.set_options((p, p) for p in self.producer_list)
        self.data = PRODUCER_MAP[event.value].recipes

        self.add_producer_column = sel.value == all_recipes_producer.name
        self.sort()

        self.set_filt(None)

    def sort(self):
        if self.add_producer_column:
            self.data_sorted = list(sorted(self.data, key=lambda r: PRODUCER_NAMES.index(r.producer.name)))
        else:
            self.data_sorted = self.data

    def update(self):
        def ingredient_count(attr):
            if self.data_filtered:
                return max(len(getattr(recipe, attr)) for recipe in self.data_filtered)
            else:
                return 0

        table = self.query_one(DataTable)
        table.clear(columns=True)
        max_input_count = ingredient_count("inputs")
        max_output_count = ingredient_count("outputs")
        rows = []

        sel = self.query_one(Select)

        columns = ["Producer"] if self.add_producer_column else []
        columns += (["Recipe Name"]
            + [f"Out #{i}" for i in range(max_output_count)]
            + [f"In  #{i}" for i in range(max_input_count)]
        )

        for recipe in self.data_filtered:
            rate_mult = 60 / recipe.cycle_rate
            row = []
            if self.add_producer_column:
                producer = recipe.producer
                row += [producer.name if producer else ""]
            row += [recipe.name]
            # FIXME: production per minute should somehow be included in `str(Ingredient)`, otherwise we can't filter for that
            inputs  = [Text(f"({round(ingr.count*rate_mult): >3}/min) {ingr.count: >3}x{ingr.name}", style="red") for ingr in recipe.inputs]
            outputs = [Text(f"({round(ingr.count*rate_mult): >3}/min) {ingr.count: >3}x{ingr.name}", style="green") for ingr in recipe.outputs]
            inputs += [""] * (max_input_count - len(inputs))
            outputs += [""] * (max_output_count - len(outputs))
            row += outputs
            row += inputs
            rows += [row]

        table.add_columns(*columns)
        table.add_rows(rows)


class SelectPurity(Screen[Purity]):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    data = []

    def compose(self) -> ComposeResult:
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        def bool_to_mark(a, mark="x"):
            return mark if a else ""

        self.data = [
            Purity.IMPURE,
            Purity.NORMAL,
            Purity.PURE,
        ]
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Purity")
        table.add_rows([[p.name.title()] for p in self.data])
        try:
            row = self.data.index(self.app.selected_node.purity)
        except ValueError as e:
            row = 0
        table.cursor_coordinate = Coordinate(row, 0)

    def action_cancel(self):
        self.dismiss([])

    def on_data_table_row_selected(self):
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        self.dismiss([SetCellValue(datatable.PurityCell, self.data[row])])


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
        self.first_dtree = self.FirstDTree(DPATH_DATA)
        if self.SecondDTree:
            self.second_dtree = self.SecondDTree(DPATH_DATA)

        if self.entry:
            def has_dot(value: str) -> bool:
                return "." not in value
            yield Pretty([])
            yield Input(placeholder="file name", validators=[Function(has_dot, "Don't add file extension manually"), ])

        yield self.first_dtree
        if self.SecondDTree:
            self.second_dtree = self.SecondDTree(DPATH_DATA)
            yield self.second_dtree
        yield Footer()

    @property
    def highlighted_path(self) -> Path:
        current = self.first_dtree.cursor_node
        return None if current is None else current.data.path

    def on_mount(self) -> None:
        # All these lines to simply move the cursor to the currently open file/folder
        prev_path = Path(CONFIG["last_file"])
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

            fpath = DPATH_DATA.parent / subdir / fname
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
