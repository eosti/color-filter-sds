"""Type definitions for the filter dataset"""

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

    def as_tuple(self) -> tuple[Decimal, Decimal, Decimal]:
        """Returns (x, y, Y) tuple"""
        return (self.x, self.y, self.y)


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

    def as_tuple(self) -> tuple[int, int, int]:
        """Returns (r, g, b) tuple"""
        return (self.r, self.g, self.b)

    def luminance(self) -> float:
        """Calculates Luminance (Y) of sRGB values"""
        return (
            0.2126 * self.sRGBtoLin(self.r)
            + 0.7152 * self.sRGBtoLin(self.g)
            + 0.0722 * self.sRGBtoLin(self.b)
        )

    def perceived_lightness(self) -> float:
        """Calculates perceived lightness, or L*"""
        Y = self.luminance()
        if Y <= (216 / 24389):
            return Y * (24389 / 27)
        return pow(Y, (1 / 3)) * 116 - 16

    @staticmethod
    def sRGBtoLin(channel: int) -> float:
        """Takes an sRGB 8-bit value, returns linear value between 0 and 1"""
        decimal_channel = channel / 255
        if decimal_channel <= 0.04045:
            return decimal_channel / 12.92
        return pow(((decimal_channel + 0.055) / 1.055), 2.4)


SDDict = Dict[int, Decimal]


@dataclass
class LightingFilter:
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


FilterDict = Dict[str, LightingFilter]


class FilterModel(BaseModel):
    """Schema for base filter model"""

    version: str = "0.2.0"
    filters: FilterDict
