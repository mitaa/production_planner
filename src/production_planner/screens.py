# -*- coding:utf-8 -*-

from .core import APP, CONFIG, DPATH_DATA, get_path, set_path, Producer, Purity, Recipe, PRODUCERS, PRODUCER_NAMES, PRODUCER_MAP, all_recipes_producer
from . import datatable

import os
import re
from dataclasses import dataclass

from textual import on
from textual.containers import Grid
from textual.screen import Screen, ModalScreen
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label, Button, Header, Footer, Input, Pretty, Select, DataTable
from textual.validation import Function
from textual.coordinate import Coordinate
from textual import events

from rich.text import Text


@dataclass
class SetCellValue:
    column: None
    value: None


class FilteredListSelector(Screen[Producer]):
    CSS_PATH = "FilteredListSelector.tcss"
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    cell = None
    data = []
    data_sorted = []
    data_filtered = []
    filter_str = ""
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
            self.filter_str = self.query_one(Input).value
        else:
            self.filter_str = event.value

        self.data_filtered = []
        words = re.split(r"\s+", self.filter_str)
        for item in self.data_sorted:
            item_str = str(item).lower()
            if all(word in item_str for word in words):
                self.data_filtered += [item]
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
            return mark if a else ""
        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns("Building", "Power", "Miner", "Power Gen")
        rows = []
        for p in self.data_filtered:
            rows += [[p.name, p.base_power, bool_to_mark(p.is_miner), bool_to_mark(p.is_pow_gen)]]
        table.add_rows(rows)


SELECT_PRODUCERS = [all_recipes_producer] + PRODUCERS


class SelectRecipe(FilteredListSelector):
    screen_title = "Recipes"

    def on_mount(self) -> None:
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
            Input(placeholder="<text filter>"),
            Select([(producer, producer) for producer in self.producer_listing], allow_blank=False)
        )
        yield DataTable()
        yield Footer()

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
        self.dismiss([SetCellValue(PurityCell, self.data[row])])


class SelectDataFile(Screen[str]):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    data = []

    def compose(self) -> ComposeResult:
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        fnames = list(os.scandir(DPATH_DATA))

        self.data = [[entry.name] for entry in fnames if entry.is_file() if not entry.name.startswith(".")]

        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("File Name")
        table.add_rows(self.data)
        try:
            row = self.data.index([CONFIG["last_file"]])
        except ValueError as e:
            row = 0
        table.cursor_coordinate = Coordinate(row, 0)

    def action_cancel(self):
        self.dismiss("")

    def on_data_table_row_selected(self):
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        self.dismiss(self.data[row][0])


class DataFileNamer(Screen[str]):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    data = []

    def compose(self) -> ComposeResult:
        def has_dot(value: str) -> bool:
            return "." not in value
        # def is_unique(value: str) -> bool:
        #     return not os.path.isfile(DPATH_DATA / (value + ".yaml"))

        yield Pretty([])
        yield Input(placeholder="file name", validators=[
                                                         Function(has_dot, "Don't add file extensions"),
                                                         ])
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        fnames = list(os.scandir(DPATH_DATA))

        self.data = [[entry.name] for entry in fnames if entry.is_file()]
        if [".cached.yaml"] in self.data:
            self.data.remove([".cached.yaml"])

        entry = self.query_one(Input)
        if not CONFIG["last_file"].startswith("."):
            entry.value = os.path.splitext(CONFIG["last_file"])[0]

        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("File Name")
        table.add_rows(self.data)

    @on(Input.Changed)
    def show_invalid_reasons(self, event: Input.Changed) -> None:
        # Updating the UI to show the reasons why validation failed
        if not event.validation_result.is_valid:  # (4)!
            self.query_one(Pretty).update(event.validation_result.failure_descriptions)
        else:
            self.query_one(Pretty).update([])

    def action_cancel(self):
        self.dismiss("")

    def on_input_submitted(self, event: Input.Submitted):
        if event.validation_result.is_valid:
            fname = event.value + ".yaml"
            fpath = DPATH_DATA / fname
            if fpath.is_file():
                def handle_overwrite(overwrite: bool):
                    if overwrite:
                        self.dismiss(fname)

                self.app.push_screen(OverwriteScreen(), handle_overwrite)
            else:
                self.dismiss(fname)


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
