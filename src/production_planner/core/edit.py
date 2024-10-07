# -*- coding:utf-8 -*-
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.

from dataclasses import dataclass, field
from numbers import Number

# TODO: add some ~IGNORED_AMOUNT variable to CONFIG and use that instead of hardcoded 0.01
#       use this also for column highlighting ...
def smartround(value: float | int):
    truncated_value = int(value)
    if abs(value - truncated_value) < 0.01:
        return truncated_value
    else:
        return round(value, 2)

@dataclass
class Bounds:
    lower: int = 0
    upper: int = 999_999


@dataclass
class EditValue:
    _value: int | float
    edit_input: str = None
    bounds: Bounds = field(default_factory=Bounds)
    # necessary ?
    # num_sign_is_pos: bool = True

    def __post_init__(self):
        # Move `.value` within bounds if outside
        # FIXME
        # if self.bounds:
        #     self.apply_edit(self.get_num())

        if self.edit_input is None:
            self.edit_input = str(self.get_num())

    def __str__(self):
        return str(self.value)

    def __repr__(self):
        return f"EditValue({repr(self.value)})"

    @property
    def value(self):
        if isinstance(self._value, Number):
            return smartround(self._value)
        else:
            return self._value

    @value.setter
    def value(self, value):
        self._value = value
        self.edit_input = str(self.get_num())

    def get_num(self):
        return self.value

    def set_num(self, value):
        self.value = value

    def apply_edit(self, txt: str=None) -> bool:
        if txt is None:
            txt = self.edit_input
        write_mode = True
        new = float(txt)
        if not (self.bounds.lower <= new <= self.bounds.upper):
            new = max(min(new, self.bounds.upper), self.bounds.lower)
            self.edit_input = str(new)
            write_mode = False
        self.set_num(new)
        return write_mode

    def edit_sign(self, edit_input: str, write_mode: bool) -> bool:
        if edit_input == "-" or edit_input == "+":
            self.edit_input = edit_input + self.edit_input.lstrip("-+ ")
            self.apply_edit()
            return True

    def edit_push_numeral(self, num: str, write_mode: bool) -> bool:
        prev = self.edit_input.rstrip(" ")
        ccount_min = len(str(self.bounds.lower))
        ccount_max = len(str(self.bounds.upper))

        if (ccount_min == ccount_max == 1):
            prev = num
            write_mode = False
        elif not write_mode:
            prev = num
            write_mode = True
        else:
            prev += num
            write_mode = True
        self.edit_input = prev
        return self.apply_edit()

    def edit_push_dot(self, _, write_mode: bool) -> bool:
        if "." not in self.edit_input:
            self.edit_input += "."
            return True

    def edit_offset(self, offset, write_mode: bool=False):
        prev = str(self.get_num()).strip("+-. ")
        self.edit_input = str(float(prev) + offset)
        return self.apply_edit()

    def edit_delete(self, _=None, write_mode: bool=False) -> bool:
        self.set_num(self.bounds.lower)
        return False

    def edit_backspace(self, _=None, write_mode: bool=False) -> bool:
        prev = self.edit_input[:].strip("+-. ")
        new = prev[:-1].strip(".")
        if len(new) == 0:
            new = str(self.bounds.lower)
        self.edit_input = new
        self.apply_edit()
        return True
