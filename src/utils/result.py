from typing import Never


def indent(string: str) -> str:
    return "\t" + string.replace("\n", "\n\t")


type Result[T, E: Exception] = tuple[T, Never] | tuple[Never, E]


def ok[T](value: T) -> tuple[T, Never]:
    return (value, None)  # type: ignore[return-value]


def err[E: Exception](error: E, enrichment: str | None = None) -> tuple[Never, E]:
    if enrichment is not None:
        error_message = f"{enrichment}:\n{indent(str(error))}"
        error = type(error)(error_message)
        return (None, error)  # type: ignore[return-value]
    return (None, error)  # type: ignore[return-value]
