"""Generates dataset from raw manufacturer data"""

import dataclasses
import json
import logging
from decimal import Decimal
from typing import Dict, Optional, Self

from lighting_filters.typedef import (
    RGB,
    CIECoords,
    LightingFilter,
    FilterDict,
    FilterModel,
    SDDict,
)
from openpyxl import Workbook
from rich.logging import RichHandler

logger = logging.getLogger(__name__)

RAW_JSON_DIR = "./raw"


def dict_to_cie(input_dict: dict) -> Optional[CIECoords]:
    """Converts a dict with x, y, transmission_y to a CIECoords object"""
    if input_dict is None or input_dict["x"] is None:
        return None

    return CIECoords(
        Decimal(f"{input_dict['x']:.4f}"),
        Decimal(f"{input_dict['y']:.4f}"),
        Decimal(f"{input_dict['transmission_y']:.2f}"),
    )


class LightingFilterIngest(LightingFilter):
    """Extension of LightingFilter type with ingestion functions"""

    @classmethod
    def from_apollo(cls, data: dict) -> Dict[str, Self]:
        """Converts Apollo filter data to common filter data"""
        logging.debug(data)

        if data["description"] is None:
            data["description"] = ""

        if data["conversion"] is not None:
            data["description"] += f" {data['conversion']}."

        if data["transmission"] is not None:
            trans = Decimal(f"{data['transmission']:.4f}")
        else:
            trans = None

        return {
            data["filter_id"]: cls(
                brand="Apollo",
                name=data["name"],
                desc=data["description"],
                rgb=RGB(*data["rgb"]),
                trans=trans,
            )
        }

    @classmethod
    def from_lee(cls, data: dict) -> Dict[str, Self]:
        """Converts Lee filter data to common filter data"""
        logging.debug(data)

        if data["description"] is None:
            data["description"] = ""

        source_a = dict_to_cie(data["tungsten_vals"])
        source_c = dict_to_cie(data["daylight_vals"])

        if (
            data["daylight_vals"] is not None
            and data["daylight_vals"]["transmission_y"] is not None
        ):
            # Lee defines its swatchbook transmission values as Source C %Y
            trans = Decimal(f"{(data['daylight_vals']['transmission_y'] / 100):.4f}")
        else:
            trans = None

        return {
            data["filter_id"]: cls(
                brand="Lee",
                name=data["name"],
                desc=data["description"],
                rgb=RGB(*data["rgb"]),
                trans=trans,
                sd=cls.format_sd(data["sd"]),
                src_a=source_a,
                src_c=source_c,
            )
        }

    @classmethod
    def from_rosco(cls, data: dict) -> Dict[str, Self]:
        """Converts Rosco filter data to common filter data"""
        logging.debug(data)

        if data["description"] is None:
            data["description"] = ""

        if data["transmission"] is not None:
            trans = Decimal(f"{data['transmission']:.4f}")
        else:
            trans = None

        source_a = dict_to_cie(data["source_a"])
        source_d65 = dict_to_cie(data["source_d65"])

        # Cinegel and Superlux filters will display as Roscolux
        brand = data["brand"][0]

        return {
            data["filter_id"]: cls(
                brand=brand,
                name=data["name"],
                desc=data["description"],
                rgb=RGB(*data["rgb"]),
                trans=trans,
                src_a=source_a,
                src_d65=source_d65,
            )
        }

    @staticmethod
    def format_sd(input_dict: dict) -> Optional[SDDict]:
        """Formats a dict of SD values to common format"""
        if input_dict is None:
            return None
        output = {}
        for key, val in input_dict.items():
            output[int(key)] = Decimal(f"{val:.5f}")

        return output


def ingest_apollo() -> FilterDict:
    """Ingest Apollo filter data from raw JSON"""
    with open(f"{RAW_JSON_DIR}/apollo.json", "r") as j:
        raw = json.load(j)

    apollo_filters = {}
    for f in raw:
        apollo_filters.update(LightingFilterIngest.from_apollo(f))

    logger.info("Ingested %i Apollo filters", len(apollo_filters))
    return apollo_filters


def ingest_lee() -> FilterDict:
    """Ingest Lee filter data from raw JSON"""
    with open(f"{RAW_JSON_DIR}/lee.json", "r") as j:
        raw = json.load(j)

    lee_filters = {}
    for f in raw:
        lee_filters.update(LightingFilterIngest.from_lee(f))

    logger.info("Ingested %i Lee filters", len(lee_filters))
    return lee_filters


def ingest_rosco() -> FilterDict:
    """Ingest Rosco filter data from raw JSON"""
    with open(f"{RAW_JSON_DIR}/rosco.json", "r") as j:
        raw = json.load(j)

    rosco_filters = {}
    for f in raw:
        rosco_filters.update(LightingFilterIngest.from_rosco(f))

    logger.info("Ingested %i Rosco filters", len(rosco_filters))
    return rosco_filters


def main():
    """Imports raw data into common filter format and exports as JSON with schema"""
    FORMAT = "%(message)s"
    logging.basicConfig(
        level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
    )

    all_filters = {}
    all_filters.update(ingest_apollo())
    all_filters.update(ingest_lee())
    all_filters.update(ingest_rosco())

    logger.info("Total number of filters: %i", len(all_filters))

    with open("../dataset/json_schema.json", "w") as f:
        schema = FilterModel.model_json_schema()
        f.write(json.dumps(schema, indent=2))

    with open("../dataset/filters.json", "w") as f:
        model = FilterModel(filters=all_filters)
        f.write(model.model_dump_json())

    logger.info("Dumped dataset to JSON")

    # Quick and dirty, should be cleaned up
    # TODO: color in rgb cell, export CIE xyY as individual cells, sort by gel ID
    wb = Workbook()
    ws = wb.active
    header = [x.name for x in dataclasses.fields(LightingFilter)]
    ws.append(["id"] + header)
    for key, val in all_filters.items():
        data = [key]
        for entry in header:
            if "src" in entry and getattr(val, entry) is not None:
                data.append(getattr(val, entry).to_coords())
            elif "sd" in entry and getattr(val, entry) is not None:
                data.append(getattr(val, entry) is not None)
            elif "rgb" in entry and getattr(val, entry) is not None:
                data.append(getattr(val, entry).to_hex())
            else:
                data.append(getattr(val, entry))
        ws.append(data)
    wb.save("../dataset/filters.xlsx")

    logger.info("Dumped dataset to XLSX")


if __name__ == "__main__":
    main()
