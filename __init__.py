# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

def nottest(obj):
    obj.__test__ = False
    return obj


@nottest
def press_before(keys):
    async def run_before(pilot):
        for k in keys:
            await pilot.press(k)
    return run_before


@nottest
def checkpoints(key_chunks):
    buf = []
    for chunk in key_chunks:
        buf += chunk
        yield buf[:]
