from enum import Enum


class UserFieldOperation(Enum):
    add = "add"
    replace = "replace"


class UserFieldType(Enum):
    Bool = "Bool"
    Int = "Int"
    Str = "Str"
    DictStr = "DictStr"
    ListStr = "ListStr"
