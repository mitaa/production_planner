# -*- coding:utf-8 -*-

from core import APP, CONFIG, DPATH_DATA, get_path, set_path, Producer, Purity, Recipe, PRODUCERS

import os
import re

from textual import on
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.app import App, ComposeResult
from textual.widgets import Label, Button, Header, Footer, Input, Pretty, DataTable
from textual.validation import Function
from textual.coordinate import Coordinate
from textual import events

from rich.text import Text


class FilteredListSelector(ModalScreen[Producer]):
    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]
    data = []
    data_filtered = []
    filter_str = ""
    selected = None

    def on_mount(self) -> None:
        self.header.tall = True
        self.query_one(DataTable).cursor_type = "row"
        self.set_filt()

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Footer()

    @property
    def header(self):
        return self.query_one(Header)

    def action_cancel(self):
        self.app.sub_title = ""
        self.header.tall = False
        self.dismiss(None)

    def on_data_table_row_selected(self):
        self.app.sub_title = ""
        self.header.tall = False
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        self.dismiss(self.data_filtered[row])

    def set_filt(self):
        to_filt = self.filter_str if self.filter_str else "<type anywhere>"
        self.app.sub_title = f"Filter: `{to_filt}`"

        self.data_filtered = []
        words = re.split(r"\s+", self.filter_str)
        for item in self.data:
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

        prev_filter_str = self.filter_str
        match event.key:
            case "delete":
                self.filter_str = ""
            case "backspace":
                self.filter_str = self.filter_str[:-1]
            case "space":
                event.key = " "

        if len(event.key) == 1 and event.key.isprintable():
            self.filter_str += event.key

        if prev_filter_str != self.filter_str:
            self.set_filt()




class SelectProducer(FilteredListSelector):
    screen_title = "Producers"

    def on_mount(self) -> None:
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


class SelectRecipe(FilteredListSelector):
    screen_title = "Recipes"

    def on_mount(self) -> None:
        if self.app.selected_node.is_module:
            self.app.selected_node.update_module_listings()
        self.data = self.app.selected_producer.recipes
        self.selected = self.app.selected_node.recipe
        self.app.log(repr(self.data))
        self.app.log(repr(self.selected))
        super().on_mount()

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

        for recipe in self.data_filtered:
            rate_mult = 60 / recipe.cycle_rate
            row = [recipe.name]
            inputs  = [Text(f"({round(ingr.count*rate_mult): >3}/min) {ingr.count: >3}x{ingr.name}", style="red") for ingr in recipe.inputs]
            outputs = [Text(f"({round(ingr.count*rate_mult): >3}/min) {ingr.count: >3}x{ingr.name}", style="green") for ingr in recipe.outputs]
            inputs += [""] * (max_input_count - len(inputs))
            outputs += [""] * (max_output_count - len(outputs))
            row += outputs
            row += inputs
            rows += [row]

        table.add_columns(*(["Recipe Name"]
                            + [f"Out #{i}" for i in range(max_output_count)]
                            + [f"In  #{i}" for i in range(max_input_count)]))
        table.add_rows(rows)


class SelectPurity(ModalScreen[Purity]):
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
        self.dismiss(None)

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


class DataFileNamer(ModalScreen[str]):
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
