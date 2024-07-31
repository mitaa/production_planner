#! /bin/env python
# -*- coding:utf-8 -*-

import core
from core import CONFIG, DPATH_DATA, Node, SummaryNode, NodeInstance, NodeTree, Producer, Recipe, Purity, PRODUCERS, get_path, set_path
from screens import SelectProducer, SelectPurity, SelectRecipe, SelectDataFile, DataFileNamer, OverwriteScreen
from datatable import PlannerTable, EmptyCell, SummaryCell, ProducerCell, RecipeCell, CountCell, MkCell, PurityCell, ClockRateCell, PowerCell, NumberCell

from textual import events
from textual.app import App, ComposeResult
from textual.widgets import Label, Button, Header, Footer, Input, Pretty, DataTable
from textual.coordinate import Coordinate

from rich.text import Text

import yaml

import tkinter as tk
import os
from copy import copy

from collections import OrderedDict
from itertools import zip_longest

from pprint import pprint


# The Fuel Generator, like all power generation buildings, behaves differently to power consumer buildings when overclocked. A generator overclocked to 250% only operates 202.4% faster[EA] (operates 250% faster[EX]).
# As the fuel consumption rate is directly proportional to generator power production, verify that demand matches the production capacity to ensure that Power Shards are used to their full potential. Fuel efficiency is unchanged, but consumption and power generation rates may be unexpectedly uneven[EA].


class Planner(App):
    BINDINGS = [
        ("+", "row_add", "Add"),
        ("-", "row_remove", "Remove"),
        ("ctrl+up", "move_up", "Shift Up"),
        ("ctrl+down", "move_down", "Shift Down"),
        ("s", "save", "Save"),
        ("l", "load", "Load"),
        ("d", "delete", "Delete"),
        ("ctrl+left", "collapse", "Collapse"),
        ("ctrl+right", "expand", "Expand"),
        ("f2", "show_hide", "Show/Hide"),
        ("f3", "swap_vis_space", "Swap Shown/Hidden"),
    ]

    # 1-Building Name, 2-Recipe Name, 3-QTY, 4-Mk, 5-Purity, 6-Clockrate        //, 7-Energy, 8*-Inputs, 9*-Outputs
    columns = []
    data = None             # total node list
    rows = []               # text-like representation of filtered node list
    summary_recipe = None
    num_write_mode = False
    selected_producer = None
    selected_node = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield PlannerTable()
        yield Footer()

    def on_mount(self) -> None:
        core.APP = self
        if not DPATH_DATA.is_dir():
            os.makedirs(DPATH_DATA)
        self.title = CONFIG["last_file"]

        p = PRODUCERS[0]
        self.planner_nodes = []
        for p in PRODUCERS:
            if not p.recipes:
                print("WHAT")
                continue
            self.planner_nodes += [Node(p, p.recipes[0])]

        table = self.query_one(PlannerTable)
        table.zebra_stripes = True
        self.data = NodeTree.from_nodes(self, [])
        # TODO: add modified marked if cached/in-memory != saved file
        self.load_data(skip_on_nonexist=True)
        self.update()

    def load_data(self, fname=".cached.yaml", skip_on_nonexist=False) -> bool:
        fpath = DPATH_DATA / fname
        if not fpath.is_file():
            if not skip_on_nonexist:
                self.notify(f"File does not exist: `{fpath}`", severity="error", timeout=10)
            return

        tree = core.load_data(fpath)
        if tree is None:
            self.notify(f"Could not parse file: `{fpath}`", severity="error", timeout=10)
        else:
            self.data = tree

        curname = os.path.splitext(CONFIG["last_file"])[0]
        self.data.reload_modules(module_stack=[curname])

        if not fname.startswith("."):
            CONFIG["last_file"] = fname
            self.title = fname
            self.notify(f"File loaded: `{fpath}`", timeout=10)

    def save_data(self, fname=".cached.yaml") -> bool:
        if not DPATH_DATA.is_dir():
            os.makedirs(DPATH_DATA)
        fpath = DPATH_DATA / fname
        with open(fpath, "w") as fp:
            yaml.dump(self.data, fp)
            if not fname.startswith("."):
                CONFIG["last_file"] = fname
                self.title = fname
                self.notify(f"File saved: `{fpath}`", timeout=10)

    def action_save(self):
        def save_file(fname: str) -> None:
            if not fname:
                self.notify("Saving File Canceled")
                return
            self.data.collect_modules()
            if os.path.splitext(fname)[0] in self.data.blueprints:
                self.notify(f"Saving to `{fname}` would create recursive modules",
                            severity="error",
                            timeout=10)
                self.notify(f"Modules included: {repr(self.data.blueprints)}",
                            severity="warning",
                            timeout=10)
                return
            fpath = DPATH_DATA / fname
            self.save_data(fname)
        self.push_screen(DataFileNamer() , save_file)

    def action_load(self):
        def load_file(fname: str) -> None:
            if not fname:
                self.notify("Loading File Canceled")
                return
            fpath = DPATH_DATA / fname
            self.load_data(fname)
            self.update()
        self.push_screen(SelectDataFile() , load_file)

    def action_show_hide(self):
        self.num_write_mode = False
        table = self.query_one(PlannerTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column
        instance = self.data.get_node(row)
        if instance:
            instance.show_hide()
            self.update()
            table.cursor_coordinate = Coordinate(row, col)

    def action_swap_vis_space(self):
        self.num_write_mode = False
        table = self.query_one(PlannerTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column
        instance = self.data.get_node(row)
        if not instance:
            instance = self.data
        self.data.swap_vis_space()
        self.update()

    def action_collapse(self):
        table = self.query_one(PlannerTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column
        instance = self.data.get_node(row)
        instance.expanded = False
        self.update()
        table.cursor_coordinate = Coordinate(row, col)

    def action_expand(self):
        table = self.query_one(PlannerTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column
        instance = self.data.get_node(row)
        instance.expanded = True
        self.update()
        table.cursor_coordinate = Coordinate(row, col)

    def action_delete(self):
        def delete_file(fname: str) -> None:
            if not fname:
                self.notify("File Deletion Canceled")
                return
            fpath = DPATH_DATA / fname
            if not fpath.is_file():
                self.notify(f"File does not exist: `{fpath}`", severity="error", timeout=10)
                return
            os.remove(fpath)
        self.push_screen(SelectDataFile(), delete_file)

    def on_data_table_cell_selected(self):
        table = self.query_one(PlannerTable)
        row = table.cursor_coordinate.row

        col = table.cursor_coordinate.column
        paths = ["producer", "recipe", "", "", "purity"]
        instance = self.data.get_node(row)
        node = instance.node_main
        if isinstance(node, SummaryNode):
            return

        self.selected_producer = node.producer
        self.selected_node = node

        def set_producer(producer: Producer) -> None:
            if producer:
                node.producer = producer
                node.producer_reset()
            self.update()
            table.cursor_coordinate = Coordinate(row, col)

        def set_purity(purity: Purity) -> None:
            if purity:
                node.purity = purity
                node.update()
                self.update()
            table.cursor_coordinate = Coordinate(row, col)

        def set_recipe(recipe: Recipe) -> None:
            if recipe:
                node.recipe = recipe
                node.update()
                instance.set_module(node.recipe.name)
                curname = os.path.splitext(CONFIG["last_file"])[0]
                self.data.reload_modules([instance], module_stack=[curname])
            self.update()
            table.cursor_coordinate = Coordinate(row, col)

        if col == 0:   # Building
            self.push_screen(SelectProducer(), set_producer)
        elif col == 1: # Recipe
            self.selected_node.update_module_listings()
            self.push_screen(SelectRecipe(), set_recipe)
        elif col == 4: # Purity
            if node.producer.is_miner:
                self.push_screen(SelectPurity(), set_purity)

    def action_move_up(self):
        self.num_write_mode = False
        table = self.query_one(PlannerTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column
        node = self.data.get_node(row)

        if node and node.parent:
            node.parent.shift_child(node, -1)
            self.update()
            table.cursor_coordinate = Coordinate(node.row_idx, col)

    def action_move_down(self):
        self.num_write_mode = False
        table = self.query_one(PlannerTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column
        node = self.data.get_node(row)

        if node and node.parent:
            node.parent.shift_child(node, 1)
            self.update()
            table.cursor_coordinate = Coordinate(node.row_idx, col)

    def action_row_add(self):
        table = self.query_one(PlannerTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column

        current_node = self.data.get_node(row)

        self.data.add_children([NodeInstance(copy(self.planner_nodes[0]))],
                               at_idx=current_node)
        self.update()
        table.cursor_coordinate = Coordinate(row + 1, col)

    def action_row_remove(self):
        table = self.query_one(PlannerTable)
        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column

        if not self.data or row < 1:
            return
        del self.data[row]
        self.update()
        table.cursor_coordinate = Coordinate(row, col)

    def on_key(self, event: events.Key) -> None:
        if len(self.screen_stack) > 1:
            return
        table = self.query_one(PlannerTable)
        paths = ["", "", "count", "mk", "", "clock_rate"]
        paths = [f"node_main.{p}" if p else "" for p in paths]
        # FIXME: verify if it works

        row = table.cursor_coordinate.row
        col = table.cursor_coordinate.column
        coord = Coordinate(row, col)
        idx_data = row - 1

        node = self.data.get_node(row)

        # TODO: prevent too large numbers, if too large reset number
        if col in {2, 3, 5} and not isinstance(node.node_main, SummaryNode):
            path = paths[col]

            if len(event.key) == 1 and 58 > ord(event.key) > 47:
                prev = str(get_path(node, path))
                ccount = len(prev)
                if not self.num_write_mode:
                    prev = ""
                self.num_write_mode = True
                if ((col==2 and ccount>2) or (col==3 and ccount>0) or (col==5 and ccount>2)):
                    prev = ""
                prev += event.key
                prev = int(prev)
                if col==3 and prev > 3:
                    prev = 3
                    self.num_write_mode = False
                elif col==5 and prev > 250:
                    prev = 250
                    self.num_write_mode = False

                set_path(node, path, prev)
                node.node_main.update()
                self.update()
                table.cursor_coordinate = coord
            elif event.key == "delete":
                set_path(node, path, 0)
                node.node_main.update()
                self.num_write_mode = False
                self.update()
                table.cursor_coordinate = coord
            elif event.key == "backspace":
                prev = str(get_path(node, path))
                new = prev[:-1]
                if len(new) == 0:
                    new = 0
                set_path(node, path, int(new))
                node.node_main.update()
                self.num_write_mode = False
                self.update()
                table.cursor_coordinate = coord
            else:
                self.num_write_mode = False
        else:
            self.num_write_mode = False

    def on_data_table_cell_highlighted(self, event):
        # Highlight ingredient columns relevant to current row
        # TODO: customize highlighting
        # FIXME: can be moved into table class and avoid the unneccessary redraw
        #        just for highlighting by doing it right the first time
        table = self.query_one(PlannerTable)
        row = event.coordinate.row
        idx_data = row - 1

        instance = self.data.get_node(row)

        if instance:
            node = instance.node_main
            ingredients = [ingr.name for ingr in (node.recipe.inputs + node.recipe.outputs)]
            table.rows_to_highlight = [row]
        else:
            ingredients = []
            table.rows_to_highlight = []

        table.cols_to_highlight = [col.name in ingredients for idx, col in enumerate(self.columns)]
        table.refresh()

    def update(self):
        columns_ingredients = []
        columns = [
                    ProducerCell,
                    RecipeCell,
                    CountCell,
                    MkCell,
                    PurityCell,
                    ClockRateCell,
                    PowerCell,
                   ]

        inputs_mixed  = set()
        outputs_mixed = set()
        inputs_only  = set()
        outputs_only = set()

        nodes = self.data.get_nodes()

        for node_instance in nodes:
            node = node_instance.node_main
            inputs_mixed |= set(i.name for i in node.recipe.inputs)
            outputs_mixed |= set(o.name for o in node.recipe.outputs)

        inputs_only = inputs_mixed - outputs_mixed
        output_only = outputs_mixed - inputs_mixed

        col_add = list(inputs_only) + list((inputs_mixed|outputs_mixed)-(inputs_only|outputs_only)) + list(outputs_only)
        for column in col_add:
            IngredientColumn = type(column, (NumberCell,), {"name": column, "path": column})
            columns_ingredients += [IngredientColumn]

        self.rows = []
        sums = []
        for node_instance in nodes:
            node = node_instance.node_main
            node.update()
            is_summary = isinstance(node, SummaryNode)
            if is_summary:
                row = [EmptyCell()] * len(columns)
            else:
                row = [Column(node) for Column in columns]

            for c in col_add:
                row += [SummaryCell(node, c) if is_summary else NumberCell(node, c)]
            self.rows += [[cell.get_styled() for cell in row]]
        self.columns = (columns + columns_ingredients)

        table = self.query_one(PlannerTable)
        table.clear(columns=True)
        table.add_columns(*(c.name for c in self.columns))
        table.add_rows(self.rows)
        table.fixed_columns = 3


def main():
    planner = Planner()
    try:
        planner.run()
    finally:
        planner.save_data()
        CONFIG.save()


if __name__ == "__main__":
    main()
