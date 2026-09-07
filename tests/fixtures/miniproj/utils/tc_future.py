"""픽스처: future annotations 없는 TYPE_CHECKING 블록."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

VALUE: "Path | None" = None
