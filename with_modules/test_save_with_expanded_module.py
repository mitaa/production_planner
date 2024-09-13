# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from .. import press_before

from production_planner import Planner

import pytest


# FIXME: It seems that there is some inconsistency with the footer bindings
# being shown or not without any change to the code - some `textual` issue ?
#
# Adding the `cursor down` hopefully helps with that
@pytest.mark.parametrize("keys", (["s", "enter", "enter", "down"],))
def test_save_with_module(snap_compare, keys):
    assert snap_compare(Planner(testrun=True), terminal_size=(150, 30), run_before=press_before(keys))
