from enum import StrEnum
from typing import TypeVar

from sqlalchemy import Enum as SqlEnum

EnumT = TypeVar("EnumT", bound=StrEnum)


def enum_type(enum: type[EnumT], *, name: str) -> SqlEnum:
    return SqlEnum(
        enum,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
        create_constraint=True,
    )
