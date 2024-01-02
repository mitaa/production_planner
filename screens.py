# -*- coding:utf-8 -*-

from core import DPATH_DATA, get_path, set_path, Producer, Purity, Recipe, PRODUCERS

import os

from textual import on
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.app import App, ComposeResult
from textual.widgets import Label, Button, Footer, Input, Pretty, DataTable
from textual.validation import Function
from textual.coordinate import Coordinate

from rich.text import Text


class SelectProducer(ModalScreen[Producer]):
    data = []
    def compose(self) -> ComposeResult:
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        def bool_to_mark(a, mark="x"):
            return mark if a else ""

        self.data = PRODUCERS
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Building", "Power", "Miner", "Power Gen")
        rows = []
        for p in self.data:
            rows += [[p.name, p.base_power, bool_to_mark(p.is_miner), bool_to_mark(p.is_pow_gen)]]
        table.add_rows(rows)
        try:
            row = self.data.index(self.app.selected_node.producer)
        except ValueError as e:
            row = 0
        table.cursor_coordinate = Coordinate(row, 0)

    def on_data_table_row_selected(self):
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        self.dismiss(self.data[row])


class SelectPurity(ModalScreen[Purity]):
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

    def on_data_table_row_selected(self):
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        self.dismiss(self.data[row])


class SelectRecipe(ModalScreen[Recipe]):
    data = []
    def compose(self) -> ComposeResult:
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        def bool_to_mark(a, mark="x"):
            return mark if a else ""

        self.data = self.app.selected_producer.recipes
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        # table.add_columns(*(r.name for r in self.app.selected_producer.recipes))

        # inputs = list(zip_longest(*[recipe.inputs for recipe in self.app.selected_producer.recipes]))
        # outputs = list(zip_longest(*[recipe.outputs for recipe in self.app.selected_producer.recipes]))
        max_input_count = max(len(recipe.inputs) for recipe in self.app.selected_producer.recipes)
        max_output_count = max(len(recipe.outputs) for recipe in self.app.selected_producer.recipes)
        rows = []

        for recipe in self.app.selected_producer.recipes:
            rate_mult = 60 / recipe.cycle_rate
            row = [recipe.name]
            inputs  = [Text(f"({round(ingr.count*rate_mult): >3}/min) {ingr.count: >3}x{ingr.name}", style="red") for ingr in recipe.inputs]
            outputs = [Text(f"({round(ingr.count*rate_mult): >3}/min) {ingr.count: >3}x{ingr.name}", style="green") for ingr in recipe.outputs]
            inputs += [""] * (max_input_count - len(inputs))
            outputs += [""] * (max_output_count - len(outputs))
            row += inputs
            row += outputs
            rows += [row]

        table.add_columns(*(["Recipe Name"] + [f"I #{i}" for i in range(max_input_count)] + [f"O #{i}" for i in range(max_output_count)]))
        table.add_rows(rows)
        try:
            row = self.data.index(self.app.selected_node.recipe)
        except ValueError as e:
            row = 0
        table.cursor_coordinate = Coordinate(row, 0)

    def on_data_table_row_selected(self):
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        self.dismiss(self.data[row])


class SelectDataFile(ModalScreen[str]):
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

    def action_cancel(self):
        self.dismiss("")

    def on_data_table_row_selected(self):
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        self.dismiss(self.data[row][0])


class DataFileNamer(ModalScreen[str]):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    data = []
    def compose(self) -> ComposeResult:
        def has_dot(value: str) -> bool:
            return not "." in value
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
        if self.app.active_file != ".cached.yaml":
            entry.value = self.app.active_file.split(".")[0]

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
