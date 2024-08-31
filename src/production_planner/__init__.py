#! /bin/env python
# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Production Planner

Usage:
  production_planner
  production_planner --data-folder=<dpath>
  production_planner (-h | --help)
  production_planner --version

Options:
  -h --help             Show this screen.
  --version             Show version.
  --data-folder=<dpath> Use the specified folder-path as data-folder for this session

"""

from . import core
from .core import CONFIG, Node, SummaryNode, NodeInstance, NodeTree, Producer, Recipe, Purity, PRODUCERS, get_path, set_path
from .screens import SelectProducer, SelectPurity, SelectRecipe, SelectDataFile, SaveDataFile, SetCellValue
from .datatable import PlannerTable, Cell, EmptyCell, ProducerCell, RecipeCell, CountCell, MkCell, PurityCell, ClockRateCell, PowerCell, IngredientCell
from .datatable import SelectionContext, Selection, Reselection

import os
from copy import copy
from dataclasses import dataclass
from pathlib import Path
import importlib.metadata

from docopt import docopt

from textual import events
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from textual.coordinate import Coordinate

from rich.style import Style
from rich.color import Color

import yaml


__version__ = importlib.metadata.version("production_planner")


# The Fuel Generator, like all power generation buildings, behaves differently to power consumer buildings when overclocked. A generator overclocked to 250% only operates 202.4% faster[EA] (operates 250% faster[EX]).
# As the fuel consumption rate is directly proportional to generator power production, verify that demand matches the production capacity to ensure that Power Shards are used to their full potential. Fuel efficiency is unchanged, but consumption and power generation rates may be unexpectedly uneven[EA].


class Planner(App):
    CSS_PATH = "Planner.tcss"
    BINDINGS = [
        ("+", "row_add", "Add"),
        ("-", "row_remove", "Remove"),
        ("ctrl+up", "move_up", "Shift Up"),
        ("ctrl+down", "move_down", "Shift Down"),
        ("ctrl+right", "expand", "Expand"),
        ("ctrl+left", "collapse", "Collapse"),
        ("s", "save", "Save"),
        ("l", "load", "Load"),
        ("d", "delete", "Delete"),
        ("f2", "show_hide", "Show/Hide"),
        ("f3", "swap_vis_space", "Swap Shown/Hidden"),
    ]

    # 1-Building Name, 2-Recipe Name, 3-QTY, 4-Mk, 5-Purity, 6-Clockrate        //, 7-Energy, 8*-Inputs, 9*-Outputs
    columns = []
    data = None               # NodeTree encompassing all rows
    loaded_hash = None        # To check if the file has changed
    num_write_mode = False    # Whether to concatenate to the number under the cursor or replace it
    selected_producer = None
    selected_node = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield PlannerTable()
        yield Footer()

    def on_mount(self) -> None:
        core.APP = self
        self.title = CONFIG.store["last_file"]

        p = PRODUCERS[0]
        self.planner_nodes = []
        for p in PRODUCERS:
            if not p.recipes:
                continue
            self.planner_nodes += [Node(p, p.recipes[0])]

        self.edit_columns = [ProducerCell,
                             RecipeCell,
                             CountCell,
                             MkCell,
                             PurityCell,
                             ClockRateCell,
                             PowerCell]

        self.columns = self.edit_columns[:]

        # last row at which the ingredient columns / highlights have been updated
        self.last_update_row = None

        self.table.zebra_stripes = True
        self.data = NodeTree.from_nodes([])
        self.load_data(skip_on_nonexist=True)
        self.update()

    def _normalize_data_path(self, subpath: Path) -> (Path, Path):
        root = CONFIG.dpath_data
        if subpath.is_absolute():
            try:
                subpath = subpath.relative_to(CONFIG.dpath_data)
            except ValueError:
                root = subpath.parent
                subpath = subpath.name
        return (root, subpath)

    def load_data(self, subpath=Path(".cached.yaml"), skip_on_nonexist=False) -> bool:
        root, subpath = self._normalize_data_path(subpath)
        fpath = root / subpath

        if not fpath.is_file():
            if not skip_on_nonexist:
                self.notify(f"File does not exist: `{fpath}`", severity="error", timeout=10)
            return

        tree = core.load_data(fpath)
        if tree is None:
            self.notify(f"Could not parse file: `{fpath}`", severity="error", timeout=10)
        else:
            self.data = tree

        curname = os.path.splitext(CONFIG.store["last_file"])[0]
        self.data.reload_modules(module_stack=[curname])

        fname = fpath.name
        if not fname.startswith("."):
            CONFIG.store["last_file"] = str(subpath)
            self.title = subpath
            self.notify(f"File loaded: `{subpath}`\n{root}", timeout=10)
        last_fpath = CONFIG.dpath_data / CONFIG.store["last_file"]
        tree = core.load_data(last_fpath) if last_fpath.is_file() else None
        if tree is not None:
            self.loaded_hash = hash(tree)

    def save_data(self, subpath=Path(".cached.yaml")) -> bool:
        root, subpath = self._normalize_data_path(subpath)
        fpath = root / subpath
        if not fpath.parent.is_dir():
            os.makedirs(fpath.parent)

        with open(fpath, "w") as fp:
            yaml.dump(self.data, fp)
        if not fpath.name.startswith("."):
            CONFIG.store["last_file"] = str(subpath)
            self.title = subpath
            self.notify(f"File saved: `{subpath}\n{root}`", timeout=10)
            self.loaded_hash = hash(self.data)

    def action_save(self):
        def save_file(subpath: Path) -> None:
            if not subpath:
                self.notify("Saving File Canceled")
                return
            self.data.collect_modules()
            if subpath.stem in self.data.blueprints:
                self.notify(f"Saving to `{subpath}` would create recursive modules",
                            severity="error",
                            timeout=10)
                self.notify(f"Modules included: {repr(self.data.blueprints)}",
                            severity="warning",
                            timeout=10)
                return
            self.save_data(subpath)
        self.push_screen(SaveDataFile(), save_file)

    def action_load(self):
        def load_file(subpath: Path) -> None:
            if not subpath:
                self.notify("Loading File Canceled")
                return
            self.load_data(subpath)
            self.update()
        self.push_screen(SelectDataFile(), load_file)

    def action_delete(self):
        def delete_file(subpath: Path) -> None:
            if not subpath:
                self.notify("File Deletion Canceled")
                return
            root, subpath = self._normalize_data_path(subpath)
            fpath = root / subpath

            if not fpath.is_file():
                self.notify(f"File does not exist: `{fpath}`", severity="error", timeout=10)
                return
            os.remove(fpath)
        # FIXME: if the currently open file is deleted then the modified indicator should be shown in the header
        self.push_screen(SelectDataFile(), delete_file)

    @property
    def table(self):
        return self.query_one(PlannerTable)

    def action_show_hide(self):
        self.num_write_mode = False
        selected = SelectionContext()
        if selected is None:
            return
        instance = selected.instance
        instance.show_hide()
        self.update(selected)

    def action_swap_vis_space(self):
        self.num_write_mode = False
        self.data.swap_vis_space()
        self.update()
        # FIXME: which line should be reselected?

    def action_collapse(self):
        selected = SelectionContext()
        if selected is None:
            return
        instance = selected.instance
        instance.expanded = False
        self.update(selected)

    def action_expand(self):
        selected = SelectionContext()
        if selected is None:
            return
        instance = selected.instance
        instance.expanded = True
        self.update(selected)

    def on_data_table_cell_selected(self):
        col = self.table.cursor_coordinate.column
        sel_ctxt = SelectionContext()
        instance = sel_ctxt.instance
        node = sel_ctxt.instance.node_main
        if isinstance(node, SummaryNode):
            return

        self.selected_producer = node.producer
        self.selected_node = node
        cell = self.edit_columns[col](instance) if len(self.edit_columns) > col else None

        if cell is not None and cell.selector:
            if not cell.access_guard():
                return

            def callback(assignments: [SetCellValue]):
                if assignments:
                    for ass in assignments:
                        cell = ass.column(instance)
                        cell.set(ass.value)
                    node.update()
                    self.update(sel_ctxt)
            self.push_screen(cell.selector(), callback)

    def action_move_up(self):
        self.num_write_mode = False
        selected = SelectionContext()
        if selected and selected.instance.parent:
            selected.instance.parent.shift_child(selected.instance, -1)
            self.update(selected)

    def action_move_down(self):
        self.num_write_mode = False
        selected = SelectionContext()
        if selected.instance and selected.instance.parent:
            selected.instance.parent.shift_child(selected.instance, 1)
        self.update(selected)

    def action_row_add(self):
        selected = SelectionContext(reselection=Reselection(offset=1))
        current_node = selected.instance if selected else None
        self.data.add_children([NodeInstance(copy(self.planner_nodes[0]))],
                               at_idx=current_node)
        self.update(selected)

    def action_row_remove(self):
        row = SelectionContext().row
        selected = SelectionContext(Selection(offset=-1))
        if not selected:
            return
        del self.data[row]
        self.update(selected)

    def check_action(self, action: str, parameters: tuple[object, ...]):
        is_main_screen = len(self.screen_stack) == 1
        # this is always keep inherited (?) bindings like tab switching between widgets
        is_my_binding = action in [binding for (_, binding, _) in self.__class__.BINDINGS]
        return is_main_screen or (not is_my_binding)

    def on_key(self, event: events.Key) -> None:
        if len(self.screen_stack) > 1:
            return

        sel_ctxt = SelectionContext()
        col = self.edit_columns[sel_ctxt.col] if len(self.edit_columns) > sel_ctxt.col else None
        instance = sel_ctxt.instance
        if instance is None:
            return

        node = instance.node_main

        if (col is None) or (not col(instance).access_guard() or col.read_only):
            self.num_write_mode = False
            return

        col = col(instance)
        match event.key:
            case "delete":
                self.num_write_mode = col.edit_delete()
            case "backspace":
                self.num_write_mode = col.edit_backspace()
            case _ if len(event.key) == 1 and 58 > ord(event.key) > 47:
                self.num_write_mode = col.edit_push_numeral(event.key, self.num_write_mode)
            case _:
                self.num_write_mode = False
                return
        self.update(sel_ctxt)

    def on_data_table_cell_highlighted(self, event):
        self.table.refresh()

    def update_columns(self, selected: NodeInstance = None) -> ([NodeInstance], [str]):
        columns_ingredients = []

        inputs_mixed = set()
        outputs_mixed = set()
        inputs_only = set()
        outputs_only = set()

        # implicitly adds/updates row_idx to the `NodeInstance`s
        nodes = self.data.get_nodes()

        for node_instance in nodes:
            node = node_instance.node_main
            if isinstance(node, SummaryNode):
                continue
            inputs_mixed |= set(i.name for i in node.recipe.inputs)
            outputs_mixed |= set(o.name for o in node.recipe.outputs)

        inputs_only = inputs_mixed - outputs_mixed
        outputs_only = outputs_mixed - inputs_mixed

        ingredients = sorted(outputs_only) + sorted((inputs_mixed | outputs_mixed) - (inputs_only | outputs_only)) + sorted(inputs_only)
        for ingredient in ingredients:
            IngredientColumn = type(ingredient, (IngredientCell,), {"name": ingredient, "path": ingredient})
            columns_ingredients += [IngredientColumn]
        self.columns = (self.edit_columns + columns_ingredients)
        return (nodes, ingredients)

    def _update_highlight_info(self, rows: [[Cell]]):
        # This method takes the `Cell` instances
        # so that we would be able to further control formatting with font colors and so on
        self.table.highlight_cols = []
        if not rows:
            return

        style_header_hover = self.table.get_component_rich_style("datatable--header-hover")
        style_hover = self.table.get_component_rich_style("datatable--hover")
        style_empty = Style()
        style_sum_pos = Style(bgcolor=Color.from_rgb(25, 50, 25))
        style_sum_neg = Style(bgcolor=Color.from_rgb(51, 13, 13))
        style_sum_zero = Style(bgcolor=Color.from_rgb(40, 40, 100))

        summary = rows[0][0].data.node_main if isinstance(rows[0][0].data.node_main, SummaryNode) else SummaryNode([])
        col_colours = []
        for idx, col in enumerate(self.columns):
            style = style_empty
            if col.name in summary.ingredients:
                ingredient_count = summary.ingredients[col.name]
                if ingredient_count > 0:
                    style = style_sum_pos
                elif ingredient_count < 0:
                    style = style_sum_neg
                else:
                    style = style_sum_zero
            else:
                style = style_sum_zero
            col_colours += [style]

        prev_row_idx = None

        for row in rows:
            instance = row[0].data
            if instance.row_idx == prev_row_idx:
                continue
            node = instance.node_main
            ingredients = [ingr.name for ingr in (node.recipe.inputs + node.recipe.outputs)]
            hov = (style_hover if instance.row_idx > 0 else style_header_hover)
            row_highlight = []
            for idx, col in enumerate(self.columns):
                if col.name in ingredients:
                    row_highlight += [col_colours[idx]]
                else:
                    row_highlight += [style_empty]
            self.table.highlight_cols += [row_highlight]

    def update(self, selected: SelectionContext = None):
        if self.loaded_hash != hash(self.data):
            self.title = f"*{CONFIG.store['last_file']}"
        else:
            self.title = CONFIG.store["last_file"]

        instance = selected.instance if selected else None

        nodes, ingredients = self.update_columns(instance)

        rows = []
        for node_instance in nodes:
            node = node_instance.node_main
            node.update()
            is_summary = isinstance(node, SummaryNode)
            if is_summary:
                node.update_recipe(inst.node_main for inst in node_instance.node_children)
            row = [Column(node_instance) for Column in self.edit_columns]

            for ingredient in ingredients:
                class Cell(IngredientCell):
                    vispath = ingredient
                    style_summary = is_summary

                row += [Cell(node_instance, ingredient)]
            rows += [row]

        self._update_highlight_info(rows)

        rows = [[cell.get_styled() for cell in row] for row in rows]

        self.table.clear(columns=True)
        self.table.add_columns(*(ingredients.name for ingredients in self.columns))
        self.table.fixed_columns = 3
        self.table.add_rows(rows)
        if selected:
            selected.reselect()


def main():
    arguments = docopt(__doc__, version=__version__)
    if arguments["--data-folder"]:
        CONFIG.dpath_data = Path(arguments["--data-folder"]).absolute()

    planner = Planner()
    try:
        planner.run()
    finally:
        planner.save_data()
        CONFIG.store.sync()


if __name__ == "__main__":
    main()
