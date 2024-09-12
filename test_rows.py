# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from . import press_before

from production_planner import Planner

import pytest


@pytest.mark.parametrize("keys", (["+"],
                                  ["+"] * 2,
                                  ["down"] * 6 + ["+"],
                                  ["down"] * 7 + ["+"],))
def test_rows_ADD(snap_compare, keys):
    assert snap_compare(Planner(), terminal_size=(150, 30), run_before=press_before(keys))


@pytest.mark.parametrize("keys", (["-"],
                                  ["-"] * 2,
                                  ["down"] + ["-"],
                                  ["down"] + ["-"] * 2,
                                  ["down"] + ["-"] * 7,
                                  ["down"] * 5 + ["-"],
                                  ["down"] * 6 + ["-"],))
def test_rows_REMOVE(snap_compare, keys):
    assert snap_compare(Planner(), terminal_size=(150, 30), run_before=press_before(keys))
