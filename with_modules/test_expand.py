# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .. import press_before

from production_planner import Planner

import pytest


@pytest.mark.parametrize("keys", (["down"] * 2 + ["ctrl+right"],
                                  ["down"] * 6 + ["ctrl+right"],))
def test_module_EXPAND(snap_compare, keys):
    assert snap_compare(Planner(), terminal_size=(150, 30), run_before=press_before(keys))


@pytest.mark.parametrize("keys", (["down"] * 8 + ["ctrl+left"],
                                  ["down"] * 8 + ["ctrl+left"] + ["down"] * 2 + ["ctrl+left"],))
def test_module_COLLAPSE(snap_compare, keys):
    assert snap_compare(Planner(), terminal_size=(150, 30), run_before=press_before(keys))
