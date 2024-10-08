# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from . import press_before, nottest

from production_planner import Planner

import pytest

@pytest.mark.parametrize("keys", (["down",
                                   "right",
                                   "enter",
                                   "tab",
                                   "down",
                                   "down",
                                   "down",
                                   "enter",
                                   "tab",
                                   "down",
                                   "enter"],))
def test_self_module(snap_compare, keys):
    assert snap_compare(Planner(), terminal_size=(150, 30), run_before=press_before(keys))
