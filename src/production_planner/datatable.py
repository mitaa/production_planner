# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from . import core
from .core import PRODUCERS, MODULE_PRODUCER
from .core import DataFile, ModuleFile, Node, SummaryNode, NodeInstance, NodeTree
from .cells import Cell, SetCellValue
from .cells import ProducerCell, RecipeCell, CountCell, MkCell, PurityCell, ClockRateCell, PowerCell, IngredientCell
from .screens import SelectDataFile, SaveDataFile

import os
from dataclasses import dataclass
from pathlib import Path
from copy import copy
from typing import Optional, Tuple

from textual.widgets import DataTable
from textual.coordinate import Coordinate
from textual import events

from rich.style import Style
from rich.color import Color

import yaml


@dataclass
class Selection:
    offset: int = 0


@dataclass
class Reselection:
    do:      bool = True
    offset:  int  = 0
    node: NodeInstance = None
    at_node: bool = True
    done:    bool = False


class SelectionContext:
    instance = None

    def __init__(self,
                 selection: Selection = None,
                 reselection:  Reselection = None):
        self.selection = selection or Selection()
        self.reselection = reselection or Reselection()
        self.row = core.APP.active_table.cursor_coordinate.row + self.selection.offset
        self.col = core.APP.active_table.cursor_coordinate.column
        self.instance = core.APP.active_table.nodetree.get_node(self.row) if core.APP.active_table.nodetree else None

    def __enter__(self):
        return self.instance

    def __exit__(self, exc_type, exc_value, traceback):
        no_exc = (exc_type, exc_value, traceback) == (None, None, None)
        if no_exc:
            self.reselect()

    def reselect(self):
        if self.reselection.do and not self.reselection.done:
            row = self.row
            if self.reselection.at_node and (self.reselection.node or self.instance):
                row = (self.reselection.node or self.instance).row_idx
            core.APP.active_table.cursor_coordinate = Coordinate(row + self.reselection.offset, self.col)
            self.reselection.done = True


class PlannerTable(DataTable):
    rows_to_highlight = []
    cols_to_highlight = []

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
    planner_columns = []
    data = None               # NodeTree encompassing all rows
    loaded_hash = None        # To check if the file has changed
    num_write_mode = False    # Whether to concatenate to the number under the cursor or replace it
    selected_producer = None
    selected_node = None

    def __init__(self, *args, sink=None, load_path=None, load_yaml=None, **kwargs):
        super().__init__(*args, **kwargs)
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

        self.planner_columns = self.edit_columns[:]
        self.zebra_stripes = True

        self.nodetree = NodeTree.from_nodes([])

        # FIXME: avoiding import cycle
        from . import io
        self.sink = sink if sink else io.VoidSink(self)

        if load_yaml:
            self.sink.load_yaml(load_yaml)
        elif load_path:
            self.sink.load(load_path)

    def on_mount(self) -> None:
        ...

    def save_data(self, subpath=None) -> Optional[Tuple[DataFile]]:
        result = self.sink.sink_commit(subpath)
        self.app.title = self.sink.title
        return result

    def action_save(self):
        def save_file(subpath: Path) -> None:
            if not subpath:
                self.notify("Saving File Canceled")
                return
            self.nodetree.collect_modules()
            # TODO: create a test
            if ModuleFile(subpath).id in self.nodetree.session_modules:
                self.notify(f"Saving to `{subpath}` would create recursive modules",
                            severity="error",
                            timeout=10)
                self.notify(f"Modules included: {repr(self.nodetree.session_modules)}",
                            severity="warning",
                            timeout=10)
                return
            result = self.save_data(subpath)
            if result:
                if not self.app._testrun:
                    self.notify(f"File saved: `{result.subpath}\n{result.root}`", timeout=10)
            else:
                datafile = DataFile.get(subpath)
                self.notify(f"File saving failed: `{datafile.subpath}\n{datafile.root}`",
                            severity="error",
                            timeout=10)
        self.app.push_screen(SaveDataFile(), save_file)

    def load_data(self, subpath) -> Optional[Tuple[DataFile]]:
        ret = self.sink.load(subpath)
        return ret

    def action_load(self):
        def load_file(subpath: Path) -> None:
            if not subpath:
                self.notify("Loading File Canceled")
                return
            result = self.load_data(subpath)
            if result:
                if not self.app._testrun:
                    self.notify(f"File loaded: `{result.subpath}`\n{result.root}", timeout=10)
        self.app.push_screen(SelectDataFile(), load_file)

    def apply_data(self, tree: NodeTree | None):
        if tree is not None:
            self.nodetree = tree
            if self.sink.sink.target:
                modulefile = ModuleFile(self.sink.sink.target.linkpath)
                MODULE_PRODUCER.update_module(modulefile)
                self.nodetree.reload_modules(module_stack=[modulefile.id])
            self.update()

    def action_delete(self):
        def delete_file(subpath: Path) -> None:
            if not subpath:
                self.notify("File Deletion Canceled")
                return
            datafile = DataFile.get(subpath)

            if not datafile.fullpath.is_file():
                self.notify(f"File does not exist: `{datafile.subpath}`\n{datafile.root}",
                            severity="error",
                            timeout=10)
                return
            os.remove(datafile.fullpath)
            self.app.manager.reset_sink_from_path(datafile.fullpath)
            self.notify(f"File deleted: `{datafile.subpath}`\n{datafile.root}", timeout=10)
            self.app.title = self.sink.title
        self.app.push_screen(SelectDataFile(), delete_file)

    def action_show_hide(self):
        self.num_write_mode = False
        selected = SelectionContext(None, Reselection(offset=1))
        if selected is None:
            return
        instance = selected.instance
        if instance:
            instance.show_hide()
            self.update(selected)

    def action_swap_vis_space(self):
        self.num_write_mode = False
        self.nodetree.swap_vis_space()
        self.update()
        # FIXME: which line should be reselected?

    def action_collapse(self):
        selected = SelectionContext()
        if selected is None:
            return
        instance = selected.instance
        if instance:
            instance.expanded = False
            self.update(selected)

    def action_expand(self):
        selected = SelectionContext()
        if selected is None:
            return
        instance = selected.instance
        if instance:
            instance.expanded = True
            self.update(selected)

    def on_data_table_cell_selected(self):
        col = self.cursor_coordinate.column
        sel_ctxt = SelectionContext()
        instance = sel_ctxt.instance
        node = sel_ctxt.instance.node_main
        if isinstance(node, SummaryNode):
            return

        self.selected_producer = node.producer
        self.selected_node = node
        cell = self.edit_columns[col](instance) if len(self.edit_columns) > col else None

        if cell is not None and cell.Selector:
            if not cell.access_guard():
                return

            def update(assignments):
                if assignments:
                    for ass in assignments:
                        cell = ass.column(instance)
                        cell.set(ass.value)
                    node.update()
                    self.update(sel_ctxt)

            # FIXME: https://github.com/Textualize/textual/issues/4928
            def callback(assignments: [SetCellValue]):
                self.call_after_refresh(update, assignments)

            self.app.push_screen(cell.Selector(self)(), callback)

    def action_move_up(self):
        self.num_write_mode = False
        selected = SelectionContext()
        if selected.instance and selected.instance.parent:
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
        self.nodetree.add_children([NodeInstance(copy(self.planner_nodes[1]))],
                               at_idx=current_node)
        self.update(selected)

    def action_row_remove(self):
        row = SelectionContext().row
        selected = SelectionContext(None, Reselection(offset=0))
        if not selected:
            return
        del self.nodetree[row]
        self.update(selected)

    def maybe_dirtied(self):
        self.app.title = self.sink.title

    def check_action(self, action: str, parameters: tuple[object, ...]):
        is_main_screen = len(self.app.screen_stack) == 1
        # this is always keep inherited (?) bindings like tab switching between widgets
        is_my_binding = action in [binding for (_, binding, _) in self.__class__.BINDINGS]
        return is_main_screen or (not is_my_binding)

    def on_key(self, event: events.Key) -> None:
        if len(self.app.screen_stack) > 1:
            return

        sel_ctxt = SelectionContext()
        col = self.edit_columns[sel_ctxt.col] if len(self.edit_columns) > sel_ctxt.col else None
        instance = sel_ctxt.instance
        if instance is None:
            return

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
        self.refresh()

    def update_columns(self, selected: NodeInstance = None) -> ([NodeInstance], [str]):
        columns_ingredients = []

        inputs_mixed = set()
        outputs_mixed = set()
        inputs_only = set()
        outputs_only = set()

        # implicitly adds/updates row_idx to the `NodeInstance`s
        nodes = self.nodetree.get_nodes()

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
        self.planner_columns = (self.edit_columns + columns_ingredients)
        return (nodes, ingredients)

    def _update_highlight_info(self, rows: [[Cell]]):
        # This method takes the `Cell` instances
        # so that we would be able to further control formatting with font colors and so on
        self.highlight_cols = []
        if not rows:
            return

        style_empty = Style()
        style_sum_pos = Style(bgcolor=Color.from_rgb(25, 50, 25))
        style_sum_neg = Style(bgcolor=Color.from_rgb(51, 13, 13))
        style_sum_zero = Style(bgcolor=Color.from_rgb(40, 40, 100))

        summary = rows[0][0].data.node_main if isinstance(rows[0][0].data.node_main, SummaryNode) else SummaryNode([])
        col_colours = []
        for idx, col in enumerate(self.planner_columns):
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
            row_highlight = []
            for idx, col in enumerate(self.planner_columns):
                if col.name in ingredients:
                    row_highlight += [col_colours[idx]]
                else:
                    row_highlight += [style_empty]
            self.highlight_cols += [row_highlight]

    def update(self, selected: SelectionContext = None):
        self.maybe_dirtied()
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

        self.clear(columns=True)
        self.add_columns(*(ingredients.name for ingredients in self.planner_columns))
        self.fixed_columns = 3
        self.add_rows(rows)
        if selected:
            selected.reselect()

    def _render_cell(
        self,
        row_index: int,
        column_index: int,
        base_style: Style,
        width: int,
        cursor: bool = False,
        hover: bool = False):
        """Render the given cell.

        Args:
            row_index: Index of the row.
            column_index: Index of the column.
            base_style: Style to apply.
            width: Width of the cell.
            cursor: Is this cell affected by cursor highlighting?
            hover: Is this cell affected by hover cursor highlighting?

        Returns:
            A list of segments per line.
        """
        cursor_row = self.cursor_row
        if row_index == cursor_row:
            base_style += self.get_component_rich_style("datatable--hover" if row_index > 0 else "datatable--header-hover")
        elif cursor_row < len(self.highlight_cols) and row_index >= 0:
            col_info = self.highlight_cols[cursor_row]
            if len(col_info) > column_index:
                base_style += col_info[column_index]

        return super()._render_cell(row_index,
                                    column_index,
                                    base_style,
                                    width, cursor,
                                    hover)
