import re
import shutil
import string
import unicodedata
import uuid
from typing import Callable

from .entities import *


class SNBTStream:
    """SNBT解析流"""

    def __init__(self, snbt: str):
        self.cur = 0
        self.snbt = snbt
        self.len = len(snbt)

    def peek(self, length: int):
        return self.snbt[self.cur:self.cur + length]

    def read(self, length: int = 1):
        if self.cur + length > self.len:
            return ""
        self.cur += length
        return self.snbt[self.cur - length:self.cur]

    def read_until(self, predicate: Callable[[str], bool]):
        buffer = []
        while self.cur < self.len:
            if predicate(self.snbt[self.cur]):
                break
            buffer.append(self.snbt[self.cur])
            self.cur += 1
        return "".join(buffer)


class SNBTParseError(Exception):
    """SNBT解析错误"""

    def __init__(self, message, position, snbt, length=1):
        super().__init__(message),
        self.message = message
        self.position = position
        self.snbt = snbt
        self.length = length
        self._terminal_width = None

    def __str__(self):
        if self._terminal_width is None:
            self._terminal_width = shutil.get_terminal_size((80, 20)).columns
        pos = self.position
        context_length = self._terminal_width - 4  # 留出边距
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
    """SNBT解析器"""

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

    def _parse_escape(self, char):
        """解析转义字符"""
        if char == "x":
            hex_str = self.stream.read(2)
            if len(hex_str) != 2 or not re.fullmatch(r"[0-9a-fA-F]{2}", hex_str):
                raise SNBTParseError("Invalid \\x escape", self.stream.cur - 2, self.stream.snbt, 4)
            return chr(int(hex_str, 16))
        elif char == "u":
            hex_str = self.stream.read(4)
            if len(hex_str) != 4 or not re.fullmatch(r"[0-9a-fA-F]{4}", hex_str):
                raise SNBTParseError("Invalid \\u escape", self.stream.cur - 4, self.stream.snbt, 6)
            return chr(int(hex_str, 16))
        elif char == "U":
            hex_str = self.stream.read(8)
            if len(hex_str) != 8 or not re.fullmatch(r"[0-9a-fA-F]{8}", hex_str):
                raise SNBTParseError("Invalid \\U escape", self.stream.cur - 8, self.stream.snbt, 10)
            return chr(int(hex_str, 16))
        elif char == "N":
            if self.stream.peek(1) != "{":
                raise SNBTParseError("Expected '{' after \\N", self.stream.cur - 1, self.stream.snbt, 2)
            name = self.stream.read_until(lambda x: x == "}")
            try:
                return unicodedata.lookup(name)
            except KeyError:
                raise SNBTParseError(
                    f"Unknown Unicode name: {name}",
                    self.stream.cur - len(name) - 3,
                    self.stream.snbt,
                    len(name) + 4
                )
        else:  # 经典转义（\n, \t, \" 等）
            escapes = {
                "\\": "\\", "\"": "\"", "'": "'",
                "n": "\n", "r": "\r", "t": "\t",
                "b": "\b", "f": "\f", "s": " "
            }
            return escapes.get(char, char)  # 未知转义（如 \z）原样保留

    def _is_escaped(self):
        """检查当前字符是否被转义"""
        if self.stream.cur == 0:
            return False  # 第一个字符不可能被转义

        # 从当前指针向前查找连续的 \，统计数量
        backslash_count = 0
        pos = self.stream.cur - 1
        while pos >= 0 and self.stream.snbt[pos] == "\\":
            backslash_count += 1
            pos -= 1

        # 奇数个 \ 表示当前字符被转义
        return backslash_count % 2 == 1

    def parse_string(self):
        start_pos = self.stream.cur
        self.stream.read_until(lambda x: not x.isspace())

        # 判断是否带引号
        if self.stream.peek(1) in ["\"", "\'"]:
            prefix = self.stream.read()
            end_condition = lambda x: x == prefix
        else:
            prefix = None
            end_condition = lambda x: x in ["}", "]", ",", ":"] and not self._is_escaped()

        res = []
        while True:
            char_pos = self.stream.cur
            char = self.stream.read(1)
            if not char:
                if prefix:
                    raise SNBTParseError(
                        "Unclosed string",
                        start_pos,
                        self.stream.snbt,
                        self.stream.cur - start_pos
                    )
                break

            if char == "\\":  # 转义字符
                next_char = self.stream.read(1)
                if not next_char:
                    raise SNBTParseError("Incomplete escape sequence", char_pos, self.stream.snbt, 2)
                res.append(self._parse_escape(next_char))
            elif end_condition(char):  # 终止符
                if not prefix:
                    self.stream.cur -= 1  # 非引号字符串回退指针
                break
            else:
                res.append(char)

        return TAG_String("".join(res))

    def parse_list(self):
        """列表及数组解析"""

        # 判断是否是数组
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

                # 检查类型
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
        else:  # 列表
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
        """解析compound"""
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
                if not key.value:  # 空键
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
                start_pos = self.stream.cur  # 记录值开始位置
                value = self.parse()
                if isinstance(value, TAG_String):
                    if value.value == "true":
                        value = TAG_Byte(1)
                    elif value.value == "false":
                        value = TAG_Byte(0)
                    elif value.value.startswith("bool("):
                        param_stream = SNBTStream(value.value[5:])
                        param = param_stream.read_until(lambda x: x == ")")
                        param_stream.read()
                        if param_stream.read():
                            raise SNBTParseError(
                                f"Invalid expression: {value.value}",
                                start_pos,
                                self.stream.snbt,
                                self.stream.cur - start_pos
                            )
                        parse_res = self.parse_snbt(param)
                        if parse_res.value:
                            value = TAG_Byte(1)
                        else:
                            value = TAG_Byte(0)
                    elif value.value.startswith("uuid("):
                        param_stream = SNBTStream(value.value[5:])
                        param = param_stream.read_until(lambda x: x == ")")
                        param_stream.read()
                        if param_stream.read():
                            raise SNBTParseError(
                                f"Invalid expression: {value.value}",
                                start_pos,
                                self.stream.snbt,
                                self.stream.cur - start_pos
                            )
                        parse_res = self.parse_snbt(param)
                        if not isinstance(parse_res, TAG_String):
                            raise SNBTParseError(
                                f"Invalid type at {value.value}: expected TAG_String, got {type(parse_res).__name__} ",
                                start_pos,
                                self.stream.snbt,
                                self.stream.cur - start_pos
                            )
                        value = TAG_Int_Array(self.uuid_to_int_array(parse_res.value))

                res[key.value] = value
        return res

    def parse(self):
        self.stream.read_until(lambda x: not x.isspace())
        prefix = self.stream.peek(1)
        if not prefix:
            raise SNBTParseError(
                f"Expected value at {self.stream.cur}",
                self.stream.cur,
                self.stream.snbt
            )
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

    @staticmethod
    def uuid_to_int_array(uuid_str):
        """uuid字符串转换"""

        u = uuid.UUID(uuid_str)
        # 获取UUID的128位整数表示
        uuid_int = u.int
        # 将128位整数拆分为4个32位整数
        int_array = [
            (uuid_int >> 96) & 0xFFFFFFFF,
            (uuid_int >> 64) & 0xFFFFFFFF,
            (uuid_int >> 32) & 0xFFFFFFFF,
            uuid_int & 0xFFFFFFFF
        ]
        # 处理符号位（如果需要有符号整数）
        int_array = [x if x < 0x80000000 else x - 0x100000000 for x in int_array]
        return int_array

    @classmethod
    def parse_snbt(cls, snbt: str):
        return cls(snbt).parse()
