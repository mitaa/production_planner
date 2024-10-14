# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from . import press_before

from production_planner import Planner

import pytest


@pytest.mark.parametrize("keys", (["7"],
                                  ["7"] * 2,
                                  ["7"] * 3,
                                  ["7"] * 4,
                                  ["7"] * 5,
                                  ["delete"],
                                  ["backspace"],
                                  ["7"] * 3 + ["backspace"],
                                  ["7"] * 3 + ["backspace", "3"],
                                  ["7"] * 4 + ["backspace"],
                                  ["2", ".", "3", "2"]))
def test_num_inputs_QTY(snap_compare, keys):
    nav = ["down"] + ["right"] * 2
    assert snap_compare(Planner(), terminal_size=(150, 30), run_before=press_before(nav + keys))


@pytest.mark.parametrize("keys", (["7"],
                                  ["0"],
                                  ["1"],
                                  ["2"],
                                  ["3"],
                                  ["1"] * 2,
                                  ["2", "delete"],
                                  ["2", "backspace"],
                                  ["2", "delete", "2"],
                                  ["7"] * 2 + ["backspace", "3"]))
def test_num_inputs_MK(snap_compare, keys):
    nav = ["down"] + ["right"] * 3
    assert snap_compare(Planner(), terminal_size=(150, 30), run_before=press_before(nav + keys))


@pytest.mark.parametrize("keys", (["7"],
                                  ["0"],
                                  ["1"],
                                  ["2"],
                                  ["3"],
                                  ["1"] * 2,
                                  ["2", "delete"],
                                  ["2", "backspace"],
                                  ["2", "delete", "2"],
                                  ["7"] * 2 + ["backspace", "3"]))
def test_num_inputs_PURITY(snap_compare, keys):
    nav = ["down"] + ["right"] * 4
    assert snap_compare(Planner(), terminal_size=(150, 30), run_before=press_before(nav + keys))


@pytest.mark.parametrize("keys", (["7"],
                                  ["7"] * 2,
                                  ["7"] * 3,
                                  ["7"] * 4,
                                  ["7"] * 5,
                                  ["delete"],
                                  ["backspace"],
                                  ["7"] * 3 + ["backspace"],
                                  ["7"] * 3 + ["backspace", "backspace", "3"],
                                  ["2", ".", "3", "2"]))
def test_num_inputs_CLOCKRATE(snap_compare, keys):
    nav = ["down"] + ["right"] * 5
    assert snap_compare(Planner(), terminal_size=(150, 30), run_before=press_before(nav + keys))


@pytest.mark.parametrize("keys", (["7"],
                                  ["7"] * 2,
                                  ["7"] * 3,
                                  ["7"] * 4,
                                  ["7"] * 5,
                                  ["delete"],
                                  ["backspace"],
                                  ["7"] * 3 + ["backspace", "delete"],
                                  ["7"] * 3 + ["backspace"],
                                  ["2", ".", "3", "2"],
                                  ["2", ".", "3", "2", "backspace"]))
def test_num_inputs_CLAMP(snap_compare, keys):
    nav = ["down"] + ["right"] * 9
    assert snap_compare(Planner(), terminal_size=(150, 30), run_before=press_before(nav + keys))


# tests that increment hotkey works and that new nodes have independent QTY attributes
# (i.e. that incrementing one nodes QTY doesn't increment the other nodes QTY)
@pytest.mark.parametrize("keys", (["+",
                                   "up",
                                   "+",
                                   "right", "right",
                                   "]", "]"],))
def test_increment_new_nodes(snap_compare, keys):
    assert snap_compare(Planner(), terminal_size=(150, 30), run_before=press_before(keys))
