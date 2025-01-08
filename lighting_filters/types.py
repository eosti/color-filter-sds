from decimal import Decimal
from typing import Dict, Optional

from pydantic import BaseModel, Field
from pydantic.dataclasses import dataclass


@dataclass
class CIECoords:
    """Dataclass for CIE xyY coordinates"""

    x: Decimal = Field(
        ge=0, le=1, title="x", description="CIE1931 chromaticity coordinate x"
    )
    y: Decimal = Field(
        ge=0, le=1, title="y", description="CIE1931 chromaticity coordinate y"
    )
    Y: Decimal = Field(
        ge=0, le=100, title="Y", description="CIE1931 tristimulus coordinate Y"
    )

    def to_coords(self) -> str:
        """Returns string-based coordinates"""
        return f"({self.x}, {self.y}, {self.Y})"


@dataclass
class RGB:
    """Dataclass for RGB values"""

    r: int = Field(
        ge=0, le=255, title="r", description="Red value, 8-bit representation"
    )
    g: int = Field(
        ge=0, le=255, title="g", description="Green value, 8-bit representation"
    )
    b: int = Field(
        ge=0, le=255, title="b", description="Blue value, 8-bit representation"
    )

    def to_hex(self) -> str:
        """Returns hexcode of RGB coords"""
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"


SDDict = Dict[int, Decimal]


@dataclass
class ColorFilter:
    """Dataclass for common filter information"""

    brand: str = Field(title="Brand", description="Brand or family of filter")
    name: str = Field(title="Filter name")
    desc: str = Field(title="Filter description")
    rgb: RGB = Field(title="RGB", description="Equivalent RGB value of filter")
    trans: Optional[Decimal] = Field(
        default=None,
        title="Transmission",
        description="Transmission of the filter",
        ge=0,
        le=1,
    )
    sd: Optional[SDDict] = Field(default=None, title="Spectral distribution")
    src_a: Optional[CIECoords] = Field(default=None, title="Source A xyY coordinates")
    src_c: Optional[CIECoords] = Field(default=None, title="Source C xyY coordinates")
    src_d65: Optional[CIECoords] = Field(
        default=None, title="Source D65 xyY coordinates"
    )


FilterDict = Dict[str, ColorFilter]


class FilterModel(BaseModel):
    """Schema for base filter model"""

    version: str = "0.2.0"
    filters: FilterDict
