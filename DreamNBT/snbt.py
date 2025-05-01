import string
from typing import Callable
import shutil

from .entities import *


class SNBTStream:
    def __init__(self, snbt: str):
        self.cur = 0
        self.snbt = snbt
        self.len = len(snbt)

    def peek(self, length: int):
        return self.snbt[self.cur:self.cur + length]

    def read(self, length: int = 1):
        if self.cur + length >= self.len:
            return ""
        self.cur += length
        return self.snbt[self.cur - length:self.cur]

    def read_until(self, predicate: Callable[[str], bool]):
        res = ""
        while self.cur < self.len:
            if predicate(self.snbt[self.cur]):
                break
            res += self.snbt[self.cur]
            self.cur += 1
        return res


class SNBTParseError(Exception):
    def __init__(self, message, position, snbt, length=1):
        super().__init__(message),
        self.message = message
        self.position = position
        self.snbt = snbt
        self.length = length

    def __str__(self):
        pos = self.position
        # 获取终端宽度，默认使用 80 列宽
        terminal_width = shutil.get_terminal_size((80, 20)).columns
        context_length = terminal_width - 4  # 留出边距
        half_context = context_length // 2
        disp_str = self.snbt

        if len(self.snbt) > context_length:
            start = max(0, pos - half_context)
            end = min(len(self.snbt), pos + half_context)
            disp_str = self.snbt[start:end]
            if start > 0:
                disp_str = "..." + disp_str
                pos = pos - start + 3
            if end < len(self.snbt):
                disp_str = disp_str + "..."

        indicator = " " * pos + "^" * self.length
        return f"SNBTParseError: {self.message}\n{disp_str}\n{indicator}"


class SNBTParser:
    def __init__(self, snbt: str):
        self.stream = SNBTStream(snbt)
        self.last_type = None

    def parse_number(self):
        end_values = ['}', ']', ',']
        start_pos = self.stream.cur
        number = self.stream.read_until(lambda x: x in end_values)
        number = number.lower()
        unsigned = False
        is_float = False
        if number.startswith("0x") or number.startswith("0b"):
            number = number.replace("_", "")
            num_type = TagId.TAG_INT
            limit = 2147483648
        else:
            if number.endswith('b'):
                num_type = TagId.TAG_BYTE
                number = number[:-1]
                limit = 128
                if number.endswith('u'):
                    unsigned = True
                    number = number[:-1]
                    limit = 256
                elif number.endswith('s'):
                    number = number[:-1]
            elif number.endswith('s'):
                num_type = TagId.TAG_SHORT
                number = number[:-1]
                limit = 2147483648
                if number.endswith('u'):
                    unsigned = True
                    number = number[:-1]
                    limit = 4294967296
                elif number.endswith('s'):
                    number = number[:-1]
            elif number.endswith('l'):
                num_type = TagId.TAG_LONG
                number = number[:-1]
                limit = 9223372036854775808
                if number.endswith('u'):
                    unsigned = True
                    number = number[:-1]
                    limit = 18446744073709551616
                elif number.endswith('s'):
                    number = number[:-1]
            elif number.endswith('i'):
                num_type = TagId.TAG_INT
                number = number[:-1]
                limit = 2147483648
                if number.endswith('u'):
                    unsigned = True
                    number = number[:-1]
                    limit = 4294967296
                elif number.endswith('s'):
                    number = number[:-1]
            elif number.endswith('f'):
                is_float = True
                number = number[:-1]
                num_type = TagId.TAG_FLOAT
                limit = 3.40282346639e+38
            elif number.endswith('d'):
                is_float = True
                number = number[:-1]
                num_type = TagId.TAG_DOUBLE
                limit = 1.7976931348623157e+308
            else:
                if "." in number or "e" in number:
                    is_float = True
                    num_type = TagId.TAG_DOUBLE
                    limit = 1.7976931348623157e+308
                else:
                    num_type = TagId.TAG_INT
                    limit = 2147483648

        try:
            if is_float:
                res = float(number)
            else:
                res = int(number, 0)
        except ValueError:
            raise SNBTParseError(
                "Invalid number: " + number,
                start_pos,
                self.stream.snbt,
                self.stream.cur - start_pos,
            )
        if unsigned:
            if not (0 <= res < limit):
                raise SNBTParseError(
                    f"Number {number} out of range",
                    start_pos,
                    self.stream.snbt,
                    self.stream.cur - start_pos,
                )
            bit_width = {
                TagId.TAG_BYTE: 8,
                TagId.TAG_SHORT: 16,
                TagId.TAG_INT: 32,
                TagId.TAG_LONG: 64,
            }
            max_unsigned = 2 ** bit_width[num_type]
            if res >= max_unsigned // 2:
                res -= max_unsigned
        else:
            if not (-limit <= res < limit):
                raise SNBTParseError(
                    f"Number {number} out of range",
                    start_pos,
                    self.stream.snbt,
                    self.stream.cur - start_pos,
                )

        return get_tag_class(num_type)(res)

    def parse_string(self):
        self.stream.read_until(lambda x: not x.isspace())
        if self.stream.peek(1) in ["\"", "\'"]:
            prefix = self.stream.read()
            res = self.stream.read_until(lambda x: x == prefix).lstrip()
            self.stream.read()
        else:
            res = self.stream.read_until(lambda x: x in ["}", "]", ",", ":"])

        return TAG_String(res)

    def parse_list(self):
        if self.stream.peek(3) == "[I;":
            self.stream.read(3)
            list_type = TagId.TAG_INT_ARRAY
        elif self.stream.peek(3) == "[B;":
            self.stream.read(3)
            list_type = TagId.TAG_BYTE_ARRAY
        elif self.stream.peek(3) == "[L;":
            self.stream.read(3)
            list_type = TagId.TAG_LONG_ARRAY
        else:
            list_type = TagId.TAG_LIST
            self.stream.read()
        value = []
        index = 0  # 数组索引
        while True:
            if self.stream.peek(1) == "]":
                self.stream.read()
                break
            if self.stream.peek(1) == ",":
                self.stream.read()
            else:
                element_start_pos = self.stream.cur  # 记录元素开始位置
                number = self.parse()
                if list_type == TagId.TAG_INT_ARRAY and not isinstance(number, TAG_Int):
                    raise SNBTParseError(
                        f"Invalid type at index {index}: expected TAG_Int, got {type(number).__name__}",
                        element_start_pos,
                        self.stream.snbt,
                        self.stream.cur - element_start_pos,
                    )
                elif list_type == TagId.TAG_BYTE_ARRAY and not isinstance(number, TAG_Byte):
                    raise SNBTParseError(
                        f"Invalid type at index {index}: expected TAG_Byte, got {type(number).__name__}",
                        element_start_pos,
                        self.stream.snbt,
                        self.stream.cur - element_start_pos,
                    )
                elif list_type == TagId.TAG_LONG_ARRAY and not isinstance(number, TAG_Long):
                    raise SNBTParseError(
                        f"Invalid type at index {index}: expected TAG_Long, got {type(number).__name__}",
                        element_start_pos,
                        self.stream.snbt,
                        self.stream.cur - element_start_pos,
                    )
                else:
                    value.append(number)
                    index += 1
        if list_type == TagId.TAG_INT_ARRAY:
            return TAG_Int_Array([ele.value for ele in value])
        elif list_type == TagId.TAG_BYTE_ARRAY:
            return TAG_Byte_Array(bytearray([ele.value for ele in value]))
        elif list_type == TagId.TAG_LONG_ARRAY:
            return TAG_Long_Array([ele.value for ele in value])
        else:
            types = [type(ele) for ele in value]
            if len(set(types)) == 1:
                return TAG_List(value)
            else:
                value_new = []
                for ele in value:
                    if isinstance(ele, TAG_Compound):
                        value_new.append(ele)
                    else:
                        comp = TAG_Compound()
                        comp[""] = ele
                        value_new.append(comp)
                return TAG_List(value_new)

    def parse_compound(self):
        res = TAG_Compound()
        self.stream.read()
        while True:
            if self.stream.peek(1) == "}":
                self.stream.read()
                break
            if self.stream.peek(1) == ",":
                self.stream.read()
            else:
                key = self.parse_string()
                if not key.value:
                    raise SNBTParseError(
                        f"Expected str at {self.stream.cur}",
                        self.stream.cur,
                        self.stream.snbt
                    )
                split = self.stream.read()
                if split != ":":
                    raise SNBTParseError(
                        f"Expected : at {self.stream.cur}",
                        self.stream.cur,
                        self.stream.snbt
                    )
                value = self.parse()
                if isinstance(value, TAG_String):
                    if value.value == "true":
                        value = TAG_Byte(1)
                    elif value.value == "false":
                        value = TAG_Byte(0)
                    elif value.value.startswith("bool("):
                        param_stream = SNBTStream(value.value[5:])
                        param = param_stream.read_until(lambda x: x == ")")
                        if param_stream.read():
                            raise ValueError(f"Invalid expression: {value.value}")
                        parse_res = self.parse_snbt(param)
                        if parse_res.value:
                            value = TAG_Byte(1)
                        else:
                            value = TAG_Byte(0)
                res[key.value] = value
        return res

    def parse(self):
        self.stream.read_until(lambda x: not x.isspace())
        prefix = self.stream.peek(1)
        if prefix == "{":
            return self.parse_compound()
        elif prefix == "[":
            return self.parse_list()
        elif prefix in string.digits + "+-":
            return self.parse_number()
        elif prefix in ["\"", "\'"]:
            return self.parse_string()
        else:
            return self.parse_string()

    @classmethod
    def parse_snbt(cls, snbt: str):
        return cls(snbt).parse()
