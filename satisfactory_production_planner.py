#! /bin/env python
# -*- coding:utf-8 -*-

from core import Node, Producer, Recipe, Purity, PRODUCERS, get_path, set_path
from screens import SelectProducer, SelectPurity, SelectRecipe, SelectDataFile, DataFileNamer, OverwriteScreen
from datatable import ProducerCell, RecipeCell, CountCell, MkCell, PurityCell, ClockRateCell, PowerCell, NumberCell

from textual import events
from textual.app import App, ComposeResult
from textual.widgets import Label, Button, Header, Footer, Input, Pretty, DataTable
from textual.coordinate import Coordinate

from rich.text import Text

import yaml

import appdirs

import tkinter as tk
import os
from copy import copy
from pathlib import Path

from collections import OrderedDict
from itertools import zip_longest

from pprint import pprint


# The Fuel Generator, like all power generation buildings, behaves differently to power consumer buildings when overclocked. A generator overclocked to 250% only operates 202.4% faster[EA] (operates 250% faster[EX]).
# As the fuel consumption rate is directly proportional to generator power production, verify that demand matches the production capacity to ensure that Power Shards are used to their full potential. Fuel efficiency is unchanged, but consumption and power generation rates may be unexpectedly uneven[EA].


class Column:
    def __init__(self, name, read_only=True):
        self.name = name
        self.read_only = read_only



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
    cells = []
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
                prev = str(get_path(self.data[idx_data], path))
                ccount = len(prev)
                if not self.num_write_mode:
                    prev = ""
                self.num_write_mode = True
                if ((col==2 and ccount>2) or (col==3 and ccount>0) or (col==5 and ccount>2)):
                    prev = ""
                    self.num_write_mode = False
                prev += event.key
                prev = int(prev)
                if col==3 and prev > 3:
                    prev = 3
                    self.num_write_mode = False
                elif col==5 and prev > 250:
                    prev = 250
                    self.num_write_mode = False

                set_path(self.data[idx_data], path, prev)
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
