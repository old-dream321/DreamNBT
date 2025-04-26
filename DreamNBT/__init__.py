from .entities import *
from typing import Union
from .snbt import SNBTParser


def parse_binary(binary: Union[BytesIO, bytes]) -> TAG_Compound:
    if isinstance(binary, bytes):
        binary = BytesIO(binary)

    root_tag_id = TagId(Struct('<b').unpack(binary.read(1))[0])
    root_tag_length = TAG_Short(binary=binary).value
    return get_tag_class(root_tag_id)(binary=binary)


def parse_snbt(snbt: str) -> TAG_Compound:
    return SNBTParser(snbt).parse()
