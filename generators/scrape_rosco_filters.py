import dataclasses
import json
import logging
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from rich.logging import RichHandler
from rich.progress import track

logger = logging.getLogger(__name__)

MYCOLOR_BASE_URL = "https://legacy.rosco.com/mycolor/mycolor.cfm"
TECHSHEET_BASE_URL = "https://legacy.rosco.com/mycolor/TechSheet.cfm"


class FilterParsingError(Exception):
    """Exception for expected issues when scraping"""


@dataclasses.dataclass
class CIECoords:
    x: float
    y: float
    transmission_y: float


@dataclasses.dataclass
class RoscoFilter:
    filter_id: str
    name: str
    description: str
    rgb: tuple[int, int, int]
    transmission: Optional[float]
    source_a: CIECoords
    source_d65: CIECoords
    brand: List[str]


class EnhancedJSONEncoder(json.JSONEncoder):
    """Helper for packing dataclasses"""

    def default(self, o):
        """Unpacks a dataclass into a dict"""
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


def get_available_filters():
    """Pulls all available filters from the MyColor app"""
    page = requests.get(MYCOLOR_BASE_URL)
    soup = BeautifulSoup(page.content, "html.parser")

    all_colors = soup.find_all("div", class_="colorSquareCenter")

    ret = []
    for i in all_colors:
        color_id = i["id"]
        # RGB data is most easily found at this stage
        color_rgb = i["style"].split("background:#")[1]
        ret.append((color_id, color_rgb))

    # Filters are sorted chromatically by default
    logger.info("Collected %i colors", len(ret))
    return ret


def parse_html_table(table):
    data = []
    rows = table.find_all("tr")

    for row in rows:
        cols = row.find_all("td")
        col_data = [e.text.strip() for e in cols]
        data.append(col_data)

    return data


def normalize_source(input: CIECoords) -> CIECoords:
    """By convention, x and y <= 1 and Y <= 100"""
    # Some Rosco colors specify x and y as a percentage, which we don't want
    if input.x > 1 or input.y > 1:
        return CIECoords(input.x / 100, input.y / 100, input.transmission_y)

    return input


def parse_rgb(input: str) -> tuple[int, int, int]:
    return tuple(int(input[i : i + 2], 16) for i in (0, 2, 4))



def get_techsheet(filter_id: str):
    body = requests.post(TECHSHEET_BASE_URL, {"ColorLabel": filter_id})
    soup = BeautifulSoup(body.content, "html.parser")

    # Parent table for page formatting
    parent_table = soup.find("table", class_="colorData")
    assert parent_table is not None
    # Child tables with actual data
    color_table = parent_table.find_all("table")[0]
    transmission_table = parent_table.find_all("table")[1]
    color_data = parse_html_table(color_table)

    # The table formatting from Rosco is nasty, so just trust me on this one
    ret = {}
    ret["brand"] = color_data[0][1]
    ret["full_name"] = color_data[1][1]
    ret["source_a"] = CIECoords(
        float(color_data[2][3]), float(color_data[3][3]), float(color_data[1][3])
    )
    ret["source_d65"] = CIECoords(
        float(color_data[2][5]), float(color_data[3][5]), float(color_data[1][5])
    )
    ret["description"] = color_data[4][1]
    ret["additional_info"] = color_data[5][1]
    ret["image_url"] = transmission_table.find("img")["src"]
    ret["transmission"] = color_data[2][1]

    return ret


def parse_filter(id_tuple: tuple, techsheet: dict) -> RoscoFilter:
    if "G N" in techsheet["full_name"]:
        # Special case of GamColor
        filter_id = " ".join(techsheet["full_name"].split(" ", 2)[:2])
        filter_name = techsheet["full_name"].split(" ", 2)[2]
    else:
        filter_id = techsheet["full_name"].split(" ", 1)[0]
        filter_name = techsheet["full_name"].split(" ", 1)[1]

    logging.debug("%s (%s)", filter_id, filter_name)

    rgb = parse_rgb(id_tuple[1])

    try:
        transmission = (
            float(techsheet["transmission"].split(" ")[0].replace("%", "")) / 100
        )
    except ValueError:
        # ex. P3699 is really weird transmission-wise, diffusion doesn't have this value
        logger.info(
            "Unable to parse transmission for %s of %s",
            filter_id,
            techsheet["transmission"],
        )
        transmission = None

    if techsheet["additional_info"] != "":
        techsheet["description"] += f" {techsheet['additional_info']}."

    # Clean up double periods and unicode degree signs
    techsheet["description"] = (
        techsheet["description"].replace("..", ".").replace("\u00b0", "")
    )

    source_a = normalize_source(techsheet["source_a"])
    source_d65 = normalize_source(techsheet["source_d65"])

    return RoscoFilter(
        filter_id=filter_id,
        name=filter_name,
        description=techsheet["description"],
        rgb=rgb,
        transmission=transmission,
        source_a=source_a,
        source_d65=source_d65,
        brand=techsheet["brand"].split(", "),
    )


def main():
    """Scrapes all filters from Rosco's website"""
    FORMAT = "%(message)s"
    logging.basicConfig(
        level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
    )

    filter_names = get_available_filters()
    filters = []
    for i in track(filter_names, description="Scraping filter information..."):
        try:
            filter_techsheet = get_techsheet(i[0])
            filters.append(parse_filter(i, filter_techsheet))
        except FilterParsingError as e:
            logger.warning("Unable to parse %s", i)
            logger.warning(e)

    logger.info("Writing to rosco.json")
    with open("raw/rosco.json", "w") as f:
        f.write(json.dumps(filters, cls=EnhancedJSONEncoder))


if __name__ == "__main__":
    main()
