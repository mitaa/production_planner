#! /bin/env python
# -*- coding:utf-8 -*-

from textual import on
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Label, Button, Header, Footer, Input, Pretty, DataTable
from textual.validation import Function
from textual.screen import ModalScreen
from textual.coordinate import Coordinate

from rich.text import Text

import yaml

import appdirs

import tkinter as tk
import json
import os
from dataclasses import dataclass
from enum import Enum
from copy import copy
import math
from pathlib import Path

from collections import OrderedDict
from itertools import zip_longest

from pprint import pprint


@dataclass
class Ingredient:
    name: str
    count: int

    def __str__(self):
        return f"({self.count}x {self.name})"


class Recipe:
    def __init__(self, name, cycle_rate, inputs, outputs):
        self.name = name
        self.cycle_rate = cycle_rate
        self.inputs = list(Ingredient(name, count) for count, name in inputs)
        self.outputs = list(Ingredient(name, count) for count, name in outputs)

    def __str__(self):
        return f"{self.name}/{self.cycle_rate} < {', '.join(map(str, self.inputs))} > {', '.join(map(str, self.outputs))}"

    def __repr__(self):
        return str(self)


class Producer:
    def __init__(self, name, *, is_miner, is_pow_gen, max_mk, base_power, recipes):
        self.name = name
        self.is_miner = is_miner
        self.is_pow_gen = is_pow_gen
        self.max_mk = max_mk
        self.base_power = base_power
        self.recipes = []
        self.recipe_map = dict()
        for k, v in recipes.items():
            recipe = Recipe(k, v[0], v[1], v[2])
            self.recipes += [recipe]
            self.recipe_map[k] = recipe


class Producers:
    def __init__(self):
        self.ingredients = set()
        self.producers = []
        self.output_ingredient_indices = Indexer()
        self.input_ingredient_indices = Indexer()
        self.output_ingredient_producers = Indexer()
        self.input_ingredient_producers = Indexer()
        self.output_ingredient_recipes = Indexer()
        self.input_ingredient_recipes = Indexer()
        self.recipe_indices = Indexer()

    def add(self, producer):
        for recip in producer.recipes:
            self.recipe_indices.add(recip.name, len(self.producers))
            for ingredient in recip.inputs:
                self.ingredients.add(ingredient.name)
                self.input_ingredient_indices.add(ingredient.name, len(self.producers))
                self.input_ingredient_producers.add(ingredient.name, producer.name)
                self.input_ingredient_recipes.add(ingredient.name, recip.name)

            for ingredient in recip.outputs:
                self.ingredients.add(ingredient.name)
                self.output_ingredient_indices.add(ingredient.name, len(self.producers))
                self.output_ingredient_producers.add(ingredient.name, producer.name)
                self.output_ingredient_recipes.add(ingredient.name, recip.name)
        self.producers += [producer]


class Indexer:
    def __init__(self):
        self.index = {}

    def add(self, k, v):
        self.index.setdefault(k, set())
        self.index[k].add(v)


class UIRow:
    def __init__(self, table, row_index, node):
        self.table = None
        self.cells = []

    def nuke(self):
        pass


class DynamicColumn:
    def __init__(self):
        pass


class ColumnOptList(DynamicColumn):
    def __init__(self):
        pass

class ColumnBuilder(ColumnOptList):
    def __init__(self):
        pass


class NodeTable:
    def __init__(self):
        self.columns = [ColumnBuilder()]


class Purity(Enum):
    NA     = 0
    PURE   = 1
    NORMAL = 2
    IMPURE = 4


class Node:
    yaml_tag = "!Node"

    def __init__(self, producer, recipe, count=1, clock_rate=100, mk=1, purity=Purity.NORMAL):
        self.producer = producer
        self.recipe = recipe
        self.count = count
        self.clock_rate = clock_rate
        self.mk = mk
        self.purity = purity if producer.is_miner else Purity.NA
        self.uirow = None
        self.ui_elems = []
        self.energy = 0

        self.ingredients = {}

        self.update()

    def producer_reset(self):
        self.recipe = self.producer.recipes[0]
        if self.producer.is_miner:
            if self.purity == Purity.NA:
                self.purity = Purity.NORMAL
        else:
            self.purity = Purity.NA
        self.energy = 0
        self.update()

    def update(self):
        self.energy = 0
        self.ingredients = {}
        rate_mult = 60/self.recipe.cycle_rate

        ingredient_mult = rate_mult * (self.clock_rate * self.count) / 100
        for inp in self.recipe.inputs:
            self.ingredients[inp.name] = int(inp.count * ingredient_mult * -1)

        for out in self.recipe.outputs:
            if self.producer.is_miner:
                self.ingredients[out.name] = int((out.count/self.purity.value) * (pow(2, self.mk)) * ingredient_mult)
            else:
                self.ingredients[out.name] = int(out.count * ingredient_mult)

        if self.producer.is_pow_gen:
            pass # TODO
        else:
            self.enegry = round(self.producer.base_power * math.pow((self.clock_rate/100), 1.321928) * self.count)


PRODUCERS = []
data_fpath = "satisfactory_production_buildings.json"
with open(data_fpath) as fp:
    data = json.load(fp)

for k, v in data.items():
    producer = Producer(k, **v)
    PRODUCERS += [producer]

PRODUCER_MAP = { p.name: p for p in PRODUCERS }

def node_representer(dumper, data):
    return dumper.represent_mapping(u"!node", {
        "producer":   data.producer.name,
        "recipe":     data.recipe.name,
        "count":      data.count,
        "clock_rate": data.clock_rate,
        "mk":         data.mk,
        "purity":     data.purity.value
    })


def node_constructor(loader, node):
    data = loader.construct_mapping(node)
    prod = PRODUCER_MAP[data["producer"]]
    node = Node(producer   = prod,
                recipe     = prod.recipe_map[data["recipe"]],
                count      = data["count"],
                clock_rate = data["clock_rate"],
                mk         = data["mk"],
                purity     = Purity(data["purity"]))
    return node

yaml.add_representer(Node, node_representer)
yaml.add_constructor(u'!node', node_constructor)


# The Fuel Generator, like all power generation buildings, behaves differently to power consumer buildings when overclocked. A generator overclocked to 250% only operates 202.4% faster[EA] (operates 250% faster[EX]).
# As the fuel consumption rate is directly proportional to generator power production, verify that demand matches the production capacity to ensure that Power Shards are used to their full potential. Fuel efficiency is unchanged, but consumption and power generation rates may be unexpectedly uneven[EA].

class PlannerTk():
    def __init__(self):
        self.window = tk.Tk()
        self.mainframe = tk.Frame(master=self.window, width=400, height=400, bg="red")
        self.mainframe.grid(row=1, column=1)
        data_fpath = "satisfactory_production_buildings.json"
        with open(data_fpath) as fp:
            data = json.load(fp)

        self.producers = Producers()


        for k, v in data.items():
            producer = Producer(k, **v)
            self.producers.add(producer)

        p = self.producers.producers[0]
        self.planner_nodes = [
            Node(p, p.recipes[0])
        ]
        pprint(self.producers.input_ingredient_recipes.index["Crude Oil"], indent=4)

        for x in self.producers.input_ingredient_recipes.index["Crude Oil"]:
            pprint(self.producers.input_ingredient_recipes.index[x], indent=6)
            y = None
            if y in self.producers.input_ingredient_recipes.index:
                for y in self.producers.input_ingredient_recipes.index[x]:
                    pprint(self.producers.input_ingredient_recipes.index[y], indent=8)

        self.nodeframe = tk.Frame(master=self.mainframe, width=400, height=400, bg="red")
        self.nodeframe.grid(row=1, column=1)

        self.bt_add_node = tk.Button(master=self.mainframe, text="Add Node", width=25, height=5)
        self.bt_add_node.grid(row=2, column=1)

        self.update()

    def update(self):
        for node in self.planner_nodes:
            for u in node.ui_elems:
                u.destroy()

        update_balance_columns = OrderedDict()
        update_balance_columns["Energy"] = "MJ"
        for node in self.planner_nodes: # collect input columns
            if node.producer.is_miner:
                update_balance_columns["Purity"] = ""
            for ingredient in node.recipe.inputs:
                update_balance_columns[ingredient.name] = "u/min"

        for node in self.planner_nodes: # collect output columns
            for ingredient in node.recipe.outputs:
                update_balance_columns[ingredient.name] = "u/min"

        print("what?")


        # 0-Building Name, 1-Recipe Name, 2-Energy, 3-Clockrate, 4-Purity, 5*-Inputs, 6*-Outputs

        for y, node in enumerate(self.planner_nodes): # fill entries
            label_name = tk.Label(self.nodeframe, text=node.producer.name, width=30, height=2)
            node.ui_elems += [label_name]
            label_name.grid(row=y, column=1)
            label_recipe = tk.Label(self.nodeframe, text=node.recipe.name, width=30, height=2)
            node.ui_elems += [label_recipe]
            label_recipe.grid(row=y, column=2)

        for node in self.planner_nodes: # enter balance totals
            pass


    def run(self):
        self.window.mainloop()


ROWS = [
    ("lane", "swimmer", "country", "time"),
    (4, "Joseph Schooling", "Singapore", 50.39),
    (2, "Michael Phelps", "United States", 51.14),
    (5, "Chad le Clos", "South Africa", 51.14),
    (6, "László Cseh", "Hungary", 51.14),
    (3, "Li Zhuhao", "China", 51.26),
    (8, "Mehdy Metella", "France", 51.58),
    (7, "Tom Shields", "United States", 51.73),
    (1, "Aleksandr Sadovnikov", "Russia", 51.84),
    (10, "Darren Burns", "Scotland", 51.84),
]

class Column:
    def __init__(self, name, read_only=True):
        self.name = name
        self.read_only = read_only



def get_path(obj, path):
    paths = path.split(".", maxsplit=1)
    primpath = paths[0]
    subpaths = paths[1:]
    if not subpaths:
        return getattr(obj, path)
    else:
        return get_path(getattr(obj, primpath), subpaths)

def set_path(obj, path, value):
    paths = path.split(".", maxsplit=1)
    primpath = paths[0]
    subpaths = paths[1:]
    if not subpaths:
        return setattr(obj, path, value)
    else:
        return set_path(getattr(obj, primpath), subpaths, value)


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
        fnames = list(os.scandir(self.app.dpath_data))

        self.data = [[entry.name] for entry in fnames if entry.is_file()]
        if [".cached.yaml"] in self.data:
            self.data.remove([".cached.yaml"])

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
        #     return not os.path.isfile(self.app.dpath_data / (value + ".yaml"))

        yield Pretty([])
        yield Input(placeholder="file name", validators=[
                                                         Function(has_dot, "Don't add file extensions"),
                                                         ])
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        fnames = list(os.scandir(self.app.dpath_data))

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
            fpath = self.app.dpath_data / fname
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


class Planner(App):
    BINDINGS = [
        ("+", "row_add", "Add"),
        ("-", "row_remove", "Remove"),
        ("ctrl+up", "move_up", "Shift Up"),
        ("ctrl+down", "move_down", "Shift Down"),
        ("s", "save", "Save"),
        ("l", "load", "Load"),
        ("d", "delete", "Delete"),
    ]

    # 1-Building Name, 2-Recipe Name, 3-QTY, 4-Mk, 5-Purity, 6-Clockrate        //, 7-Energy, 8*-Inputs, 9*-Outputs
    columns = []
    rows = []
    data = []
    num_write_mode = False
    selected_producer = None
    active_file = ".cached.yaml"

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        self.dpath_data = Path(appdirs.user_data_dir("satisfactory_production_planner", "mitaa"))
        if not self.dpath_data.is_dir():
            os.makedirs(self.dpath_data)
        self.title = self.active_file

        p = PRODUCERS[0]
        self.planner_nodes = []
        for p in PRODUCERS:
            if not p.recipes:
                print("WHAT")
                continue
            self.planner_nodes += [Node(p, p.recipes[0])]

        table = self.query_one(DataTable)
        table.zebra_stripes = True
        self.load_data(skip_on_nonexist=True)
        self.update()

    def load_data(self, fname=".cached.yaml", skip_on_nonexist=False) -> bool:
        fpath = self.dpath_data / fname
        if not fpath.is_file():
            if not skip_on_nonexist:
                self.notify(f"File does not exist: `{fpath}`", severity="error", timeout=10)
            return
        with open(fpath, "r") as fp:
            self.data = yaml.unsafe_load(fp)
            if fname != ".cached.yaml":
                self.notify(f"File loaded: `{fpath}`", timeout=10)

    def save_data(self, fname=".cached.yaml") -> bool:
        if not self.dpath_data.is_dir():
            os.makedirs(self.dpath_data)
        fpath = self.dpath_data / fname
        with open(fpath, "w") as fp:
            yaml.dump(self.data, fp)
            self.active_file = fname
            self.title = fname
            if fname != ".cached.yaml":
                self.notify(f"File saved: `{fpath}`", timeout=10)

    def action_save(self):
        def save_file(fname: str) -> None:
            if not fname:
                self.notify("Saving File Canceled")
                return
            fpath = self.dpath_data / fname
            self.save_data(fname)
        self.push_screen(DataFileNamer() , save_file)

    def action_load(self):
        def load_file(fname: str) -> None:
            if not fname:
                self.notify("Loading File Canceled")
                return
            fpath = self.dpath_data / fname
            self.load_data(fname)
            self.update()
        self.push_screen(SelectDataFile() , load_file)

    def action_delete(self):
        def delete_file(fname: str) -> None:
            if not fname:
                self.notify("File Deletion Canceled")
                return
            fpath = self.dpath_data / fname
            if not fpath.is_file():
                self.notify(f"File does not exist: `{fpath}`", severity="error", timeout=10)
                return
            os.remove(fpath)
        self.push_screen(SelectDataFile(), delete_file)

    def on_data_table_cell_selected(self):
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column
        idx_data = row - 1
        paths = ["producer", "recipe", "", "", "purity"]
        node = self.data[idx_data]

        def set_producer(producer: Producer) -> None:
            node.producer = producer
            node.producer_reset()
            self.update()
            table.cursor_coordinate = Coordinate(row, col)

        def set_purity(purity: Purity) -> None:
            node.purity = purity
            self.update()
            table.cursor_coordinate = Coordinate(row, col)

        def set_recipe(recipe: Recipe) -> None:
            node.recipe = recipe
            self.update()
            table.cursor_coordinate = Coordinate(row, col)

        if col == 0:   # Building
            node.producer_reset()
            self.push_screen(SelectProducer(), set_producer)
        elif col == 1: # Recipe
            self.selected_producer = node.producer
            self.push_screen(SelectRecipe(), set_recipe)
        elif col == 4: # Purity
            if node.producer.is_miner:
                self.push_screen(SelectPurity(), set_purity)

    def action_move_up(self):
        self.num_write_mode = False
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column
        idx_data = row - 1
        if idx_data > 0:
            buf = self.data[idx_data]
            del self.data[idx_data]
            self.data.insert(idx_data-1, buf)
            self.update()
            table.cursor_coordinate = Coordinate(row - 1, col)

    def action_move_down(self):
        self.num_write_mode = False
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column
        idx_data = row - 1
        if 0 <= idx_data < (len(self.data) - 1):
            buf = self.data[idx_data]
            del self.data[idx_data]
            self.data.insert(idx_data + 1, buf)
            self.update()
            table.cursor_coordinate = Coordinate(row + 1, col)

    def action_row_add(self):
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column
        idx_data = row
        self.data.insert(idx_data, copy(self.planner_nodes[0]))
        self.update()
        table.cursor_coordinate = Coordinate(idx_data + 1, col)

    def action_row_remove(self):
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column

        if not self.data or row < 1:
            return
        del self.data[row - 1]
        self.update()
        table.cursor_coordinate = Coordinate(row, col)

    def on_key(self, event: events.Key) -> None:
        if len(self.screen_stack) > 1:
            return
        table = self.query_one(DataTable)
        paths = ["", "", "count", "mk", "", "clock_rate"]

        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column
        coord = Coordinate(row, col)
        idx_data = row - 1
        if row == 0:
            return

        # TODO: prevent too large numbers, if too large reset number
        if col in {2, 3, 5}:
            path = paths[col]

            if len(event.key) == 1 and 58 > ord(event.key) > 47:
                if self.num_write_mode:
                    prev = str(get_path(self.data[idx_data], path))
                else:
                    prev = ""
                prev += event.key
                set_path(self.data[idx_data], path, int(prev))
                self.num_write_mode = True
                self.update()
                table.cursor_coordinate = coord
            elif event.key == "delete":
                set_path(self.data[idx_data], path, 0)
                self.num_write_mode = False
                self.update()
                table.cursor_coordinate = coord
            elif event.key == "backspace":
                prev = str(get_path(self.data[idx_data], path))
                new = prev[:-1]
                if len(new) == 0:
                    new = 0
                set_path(self.data[idx_data], path, int(new))
                self.num_write_mode = False
                self.update()
                table.cursor_coordinate = coord
            else:
                self.num_write_mode = False
        else:
            self.num_write_mode = False


    def update(self):
        self.save_data()
        columns = [
                    Column("Building Name", False),
                    Column("Recipe", False),
                    Column("QTY", False),
                    Column("Mk", False),
                    Column("Purity", False),
                    Column("Clockrate", False),
                    Column("Energy"),
                   ]

        inputs_mixed  = set()
        outputs_mixed = set()
        inputs_only  = set()
        outputs_only = set()
        x = self.data
        for node in self.data:
            inputs_mixed |= set(i.name for i in node.recipe.inputs)
            outputs_mixed |= set(o.name for o in node.recipe.outputs)

        inputs_only = inputs_mixed - outputs_mixed
        output_only = outputs_mixed - inputs_mixed

        col_add = list(inputs_only) + list((inputs_mixed|outputs_mixed)-(inputs_only|outputs_only)) + list(outputs_only)
        columns += [Column(c) for c in col_add]

        self.rows = []
        sums = []
        for node in self.data:
            node.update()
            row = [
                node.producer.name,
                node.recipe.name,
                node.count,
                node.mk if node.producer.is_miner else "",
                node.purity.name if node.purity != Purity.NA else "",
                node.clock_rate,
                node.energy,
            ]
            for c in col_add:
                row += [node.ingredients[c] if c in node.ingredients.keys() else ""]
            self.rows += [row]
        cols_to_sum = []
        for c in list(zip(*self.rows))[6:]:
            cols_to_sum += [[r if r else 0 for r in c]]
        sums = ["", "", "", "", "", ""] + list(map(sum, cols_to_sum))
        self.rows.insert(0, sums)

        table = self.query_one(DataTable)
        table.clear(columns=True)
        table.add_columns(*(c.name for c in columns))
        table.add_rows(self.rows)
        table.fixed_columns = 3


def main():
    planner = Planner()
    planner.run()


if __name__ == "__main__":
    main()
