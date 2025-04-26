from enum import Enum
from struct import Struct
from io import BytesIO
from collections.abc import MutableSequence, Sequence, MutableMapping
from typing import Optional, List


class TagId(Enum):
    TAG_END = 0
    TAG_BYTE = 1
    TAG_SHORT = 2
    TAG_INT = 3
    TAG_LONG = 4
    TAG_FLOAT = 5
    TAG_DOUBLE = 6
    TAG_BYTE_ARRAY = 7
    TAG_STRING = 8
    TAG_LIST = 9
    TAG_COMPOUND = 10
    TAG_INT_ARRAY = 11
    TAG_LONG_ARRAY = 12

    @classmethod
    def __missing__(cls, key):
        raise ValueError(f'Unknown tag id: {key}')


class TAG(object):
    id: TagId

    def __init__(self, name=None, value=None):
        self.name = name
        self.value = value

    def to_binary(self):
        raise NotImplementedError()


class TAG_End(TAG):
    id = TagId.TAG_END
    fmt = Struct('<b')

    def __init__(self):
        super().__init__()

    def to_binary(self):
        return self.fmt.pack(0)


class TAG_OneNumber(TAG):
    fmt = None
    snbt_suffix = None

    def __init__(self, value=None, name=None, binary=None):
        super().__init__(name, value)
        if binary:
            self.__parse_binary(binary)

    def __parse_binary(self, binary: BytesIO):
        self.value = self.fmt.unpack(binary.read(self.fmt.size))[0]

    def to_binary(self):
        return self.fmt.pack(self.value)

    def to_snbt(self):
        return str(self.value) + self.snbt_suffix

    def format_string(self, layer: int = 0):
        res = ""
        if layer:
            res += '  ' * layer
        res += f"{self.__class__.__name__}({self.name if self.name else ''}): {str(self.value)}"
        return res

    def __str__(self):
        return self.format_string()

    def __repr__(self):
        return self.format_string()


class TAG_Byte(TAG_OneNumber):
    id = TagId.TAG_BYTE
    fmt = Struct('<b')
    snbt_suffix = 'b'


class TAG_Short(TAG_OneNumber):
    id = TagId.TAG_SHORT
    fmt = Struct('<h')
    snbt_suffix = 's'


class TAG_Int(TAG_OneNumber):
    id = TagId.TAG_INT
    fmt = Struct('<i')
    snbt_suffix = ''


class TAG_Long(TAG_OneNumber):
    id = TagId.TAG_LONG
    fmt = Struct('<q')


class TAG_Float(TAG_OneNumber):
    id = TagId.TAG_FLOAT
    fmt = Struct('<f')
    snbt_suffix = 'f'


class TAG_Double(TAG_OneNumber):
    id = TagId.TAG_DOUBLE
    fmt = Struct('<d')
    snbt_suffix = 'd'


class TAG_Byte_Array(TAG, MutableSequence):
    id = TagId.TAG_BYTE_ARRAY

    def __init__(self, value: Optional[bytearray] = None, name=None, binary=None):
        super().__init__(name, value)
        if binary:
            self.__parse_binary(binary)

    def __parse_binary(self, binary: BytesIO):
        length = TAG_Int(binary=binary).value
        self.value = bytearray(binary.read(length))

    def to_binary(self):
        return TAG_Int(len(self.value)).to_binary() + self.value

    def to_snbt(self):
        res = "[B;"
        for i in self.value:
            res += f"{int(i)}B,"
        if res[-1] == ',':
            res = res[:-1]
        res += "]"
        return res

    def format_string(self, layer: int = 0):
        res = ""
        if layer:
            res += '  ' * layer
        res += f"{self.__class__.__name__}({self.name if self.name else ''}): {str(self.value)}"
        return res

    def __str__(self):
        return self.format_string()

    def __repr__(self):
        return self.format_string()

    def __len__(self):
        return len(self.value)

    def __getitem__(self, index):
        return self.value[index]

    def __setitem__(self, index, value):
        self.value[index] = value

    def __delitem__(self, key):
        del self.value[key]

    def __iter__(self):
        return iter(self.value)

    def insert(self, index, value):
        self.value.insert(index, value)

    def append(self, value):
        self.value.append(value)


class TAG_Int_Array(TAG, MutableSequence):
    id = TagId.TAG_INT_ARRAY

    def __init__(self, value: Optional[List[int]] = None, name=None, binary=None):
        super().__init__(name, value)
        if binary:
            self.__parse_binary(binary)

    def __parse_binary(self, binary: BytesIO):
        length = TAG_Int(binary=binary).value
        self.value = []
        for _ in range(length):
            self.value.append(TAG_Int(binary=binary).value)

    def to_binary(self):
        return TAG_Int(len(self.value)).to_binary() + b''.join(TAG_Int(value).to_binary() for value in self.value)

    def to_snbt(self):
        res = "[I;"
        for i in self.value:
            res += f"{i},"
        if res[-1] == ',':
            res = res[:-1]
        res += "]"
        return res

    def format_string(self, layer: int = 0):
        res = ""
        if layer:
            res += '  ' * layer
        res += f"{self.__class__.__name__}({self.name if self.name else ''}): {str(self.value)}"
        return res

    def __str__(self):
        return self.format_string()

    def __repr__(self):
        return self.format_string()

    def __len__(self):
        return len(self.value)

    def __getitem__(self, index):
        return self.value[index]

    def __setitem__(self, index, value):
        self.value[index] = value

    def __delitem__(self, key):
        del self.value[key]

    def __iter__(self):
        return iter(self.value)

    def insert(self, index, value):
        self.value.insert(index, value)

    def append(self, value):
        self.value.append(value)


class TAG_Long_Array(TAG, MutableSequence):
    id = TagId.TAG_LONG_ARRAY

    def __init__(self, value: Optional[List[int]] = None, name=None, binary=None):
        super().__init__(name, value)
        if binary:
            self.__parse_binary(binary)

    def __parse_binary(self, binary: BytesIO):
        length = TAG_Int(binary=binary).value
        self.value = []
        for _ in range(length):
            self.value.append(TAG_Long(binary=binary).value)

    def to_binary(self):
        return TAG_Int(len(self.value)).to_binary() + b''.join(
            TAG_Long(value=value).to_binary() for value in self.value)

    def to_snbt(self):
        res = "[B;"
        for i in self.value:
            res += f"{i}L,"
        if res[-1] == ',':
            res = res[:-1]
        res += "]"
        return res

    def format_string(self, layer: int = 0):
        res = ""
        if layer:
            res += '  ' * layer
        res += f"{self.__class__.__name__}({self.name if self.name else ''}): {str(self.value)}"
        return res

    def __str__(self):
        return self.format_string()

    def __repr__(self):
        return self.format_string()

    def __len__(self):
        return len(self.value)

    def __getitem__(self, index):
        return self.value[index]

    def __setitem__(self, index, value):
        self.value[index] = value

    def __delitem__(self, key):
        del self.value[key]

    def __iter__(self):
        return iter(self.value)

    def insert(self, index, value):
        self.value.insert(index, value)

    def append(self, value):
        self.value.append(value)


class TAG_String(TAG, Sequence):
    id = TagId.TAG_STRING

    def __init__(self, value: Optional[str] = None, name=None, binary=None):
        super().__init__(name, value)
        if binary:
            self.__parse_binary(binary)

    def __parse_binary(self, binary: BytesIO):
        length = Struct('<H').unpack(binary.read(2))[0]
        self.value = binary.read(length).decode('utf-8')

    def to_binary(self):
        return Struct('<H').pack(len(self.value)) + self.value.encode('utf-8')

    def to_snbt(self):
        return f'"{self.value}"'

    def format_string(self, layer: int = 0):
        res = ""
        if layer:
            res += '  ' * layer
        res += f'{self.__class__.__name__}({self.name if self.name else ""}): "{str(self.value)}"'
        return res

    def __str__(self):
        return self.format_string()

    def __repr__(self):
        return self.format_string()

    def __len__(self):
        return len(self.value)

    def __getitem__(self, index):
        return self.value[index]

    def __iter__(self):
        return iter(self.value)


class TAG_List(TAG, MutableSequence):
    id = TagId.TAG_LIST

    def __init__(self, value=None, name=None, binary=None, tag_id=None):
        super().__init__(name, [])
        if binary:
            self.__parse_binary(binary)
        elif value:
            self.tag_id = tag_id
            for tag in value:
                if not isinstance(tag, TAG):
                    raise TypeError(f"{tag} is not a TAG")
                if self.tag_id is None:
                    self.tag_id = tag.id
                if tag.id != self.tag_id:
                    raise ValueError(f"{tag} is not a {TagId(self.tag_id).name}")
                self.value.append(tag)

    def __parse_binary(self, binary: BytesIO):
        self.tag_id = TagId(Struct('<b').unpack(binary.read(1))[0])
        length = Struct('<i').unpack(binary.read(4))[0]
        for _ in range(length):
            self.value.append(get_tag_class(self.tag_id)(binary=binary))

    def to_binary(self):
        res = Struct('<b').pack(self.tag_id.value) + Struct('<i').pack(len(self.value))
        for tag in self.value:
            if not isinstance(tag, TAG_Compound):
                res += tag.to_binary()
            else:
                res += tag.to_binary(header=False)
        return res

    def to_snbt(self):
        res = "["
        for tag in self.value:
            if self.tag_id == TagId.TAG_COMPOUND and not tag.name:
                res += f"{tag.to_snbt()[2:-1]},"
            else:
                res += f"{tag.to_snbt()},"
        if res[-1] == ',':
            res = res[:-1]
        res += "]"
        return res

    def format_string(self, layer: int = 0):
        res = ""
        if layer:
            res += '  ' * layer
        res += f"{self.__class__.__name__}({self.name}): {len(self.value)} entries [\n"
        for tag in self.value:
            res += f"{tag.format_string(layer + 1)}\n"
        if layer:
            res += '  ' * layer
        res += "]"
        return res

    def __str__(self):
        return self.format_string()

    def __repr__(self):
        return self.format_string()

    def __len__(self):
        return len(self.value)

    def __getitem__(self, index):
        return self.value[index]

    def __setitem__(self, index, value: TAG):
        if not isinstance(value, TAG):
            raise TypeError("value must be a TAG")
        if value.id != self.tag_id:
            raise TypeError(f"value must be a {get_tag_class(self.tag_id).__name__}")
        self.value[index] = value

    def __delitem__(self, key):
        del self.value[key]

    def __iter__(self):
        return iter(self.value)

    def insert(self, index, value: TAG):
        if not isinstance(value, TAG):
            raise TypeError("value must be a TAG")
        if value.id != self.tag_id:
            raise TypeError(f"value must be a {get_tag_class(self.tag_id).__name__}")
        self.value.insert(index, value)

    def append(self, value: TAG):
        if not isinstance(value, TAG):
            raise TypeError("value must be a TAG")
        if value.id != self.tag_id:
            raise TypeError(f"value must be a {get_tag_class(self.tag_id).__name__}")
        self.value.append(value)


class TAG_Compound(TAG, MutableMapping):
    id = TagId.TAG_COMPOUND

    def __init__(self, name=None, binary=None):
        super().__init__(name, [])
        if binary:
            self.__parse_binary(binary)

    def __parse_binary(self, binary: BytesIO):
        while True:
            tag_id = TagId(Struct('<b').unpack(binary.read(1))[0])
            if tag_id == TagId.TAG_END:
                break
            tag_name = TAG_String(binary=binary).value
            new_tag = get_tag_class(tag_id)(name=tag_name, binary=binary)
            self.value.append(new_tag)

    def to_binary(self, header=True):
        if header:
            res = Struct('<b').pack(self.id.value)
            if self.name:
                res += Struct('<H').pack(len(self.name)) + self.name.encode('utf-8')
            else:
                res += Struct('<H').pack(0)
            for tag in self.value:
                # print(tag, tag.id, tag.name)
                res += Struct('<b').pack(tag.id.value) + Struct('<H').pack(len(tag.name)) + tag.name.encode('utf-8')
                if not isinstance(tag, TAG_Compound):
                    res += tag.to_binary()
                else:
                    res += tag.to_binary(header=False)
            return res + TAG_End().to_binary()
        else:
            res = b''
            for tag in self.value:
                res += Struct('<b').pack(tag.id.value) + Struct('<H').pack(len(tag.name)) + tag.name.encode('utf-8')
                if not isinstance(tag, TAG_Compound):
                    res += tag.to_binary()
                else:
                    res += tag.to_binary(header=False)
            return res + TAG_End().to_binary()

    def to_snbt(self):
        res = "{"
        for tag in self.value:
            res += f"{tag.name}:{tag.to_snbt()},"
        if res[-1] == ',':
            res = res[:-1]
        res += "}"
        return res

    def format_string(self, layer: int = 0):
        res = ""
        if layer:
            res += '  ' * layer
        res += f"{self.__class__.__name__}({self.name if self.name else ''}): {len(self.value)} entries " + "{\n"
        for tag in self.value:
            res += f"{tag.format_string(layer + 1)}\n"
        if layer:
            res += '  ' * layer
        res += "}"
        return res

    def __str__(self):
        return self.format_string()

    def __repr__(self):
        return self.format_string()

    def get(self, key, default=None):
        for tag in self.value:
            if tag.name == key:
                return tag
        return default

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value: TAG):
        if not isinstance(value, TAG):
            raise TypeError("value must be a TAG")
        for tag in self.value:
            if tag.name == key:
                value.name = key
                self.value[self.value.index(tag)] = value
                return
        value.name = key
        self.value.append(value)

    def __delitem__(self, key):
        for tag in self.value:
            if tag.name == key:
                self.value.remove(tag)
                return

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, item):
        for tag in self.value:
            if tag.name == item:
                return True
        return False

    def keys(self):
        return [tag.name for tag in self.value]

    def values(self):
        return [tag.value for tag in self.value]

    def items(self):
        return [(tag.name, tag.value) for tag in self.value]

    def __len__(self):
        return len(self.value)


def get_tag_class(tag_id: TagId):
    TAGS = {
        TagId.TAG_END: TAG_End,
        TagId.TAG_BYTE: TAG_Byte,
        TagId.TAG_SHORT: TAG_Short,
        TagId.TAG_INT: TAG_Int,
        TagId.TAG_LONG: TAG_Long,
        TagId.TAG_FLOAT: TAG_Float,
        TagId.TAG_DOUBLE: TAG_Double,
        TagId.TAG_BYTE_ARRAY: TAG_Byte_Array,
        TagId.TAG_STRING: TAG_String,
        TagId.TAG_LIST: TAG_List,
        TagId.TAG_COMPOUND: TAG_Compound,
        TagId.TAG_INT_ARRAY: TAG_Int_Array,
        TagId.TAG_LONG_ARRAY: TAG_Long_Array,
    }
    res = TAGS.get(tag_id)
    if res is None:
        raise ValueError(f'Unknown tag id: {tag_id}')
    return res
