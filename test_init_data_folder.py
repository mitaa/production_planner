# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from production_planner import Planner

import pytest


@pytest.mark.empty_data_folder
def test_init_data(snap_compare):
    app = Planner()

    async def run_before(pilot):
        for k in ["+"]:
            await pilot.press(k)
    assert snap_compare(app, terminal_size=(150, 30), run_before=run_before)
