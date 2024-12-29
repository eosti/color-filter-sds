import dataclasses
import json
import logging
import unicodedata
from pathlib import Path
from typing import List, Optional

import chompjs
import pdfplumber
from rich.logging import RichHandler
from rich.progress import track

logger = logging.getLogger(__name__)

PDF_LOCATION = "~/Downloads/apollo-pdf/"
HEX_LOCATION = "~/Downloads/colorhex.js"


class FilterParsingError(Exception):
    """Exception for expected issues when scraping"""


@dataclasses.dataclass
class ApolloBoxes:
    saturation: str
    interaction_red: str
    interaction_blue: str
    interaction_green: str
    interaction_yellow: str


@dataclasses.dataclass
class ApolloFilter:
    filter_id: str
    name: str
    description: Optional[str]
    conversion: Optional[str]
    rgb: tuple[int, int, int]
    transmission: float
    color_description: Optional[str]
    boxes: Optional[ApolloBoxes]


class EnhancedJSONEncoder(json.JSONEncoder):
    """Helper for packing dataclasses"""

    def default(self, o):
        """Unpacks a dataclass into a dict"""
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, float):
            return round(o, 4)
        return super().default(o)


def filter_similar_values(vals: List[float], distance: int = 2) -> List[int]:
    """Given a list of values, converts to ints and groups similar values together"""
    vals.sort()
    return [
        vals[i]
        for i in range(len(vals))
        if i == 0 or (vals[i] - vals[i - 1]) >= distance
    ]


def determine_boundaries(vals: List[int]) -> List[int]:
    """Given a list of values, determines the midpoint boundary"""
    vals.sort()
    return [int((vals[i] + vals[i + 1]) / 2) for i in range(len(vals) - 1)]


def filter_y_range(boxes: List[dict], upper_bound: float, lower_bound: float) -> dict:
    """Return the single object within the given y range"""
    filtered_boxes = [
        x for x in boxes if x["y0"] > lower_bound and x["y0"] <= upper_bound
    ]

    if len(filtered_boxes) != 1:
        raise RuntimeError("Not exactly one box in y range")

    return filtered_boxes[0]


def collect_pdfs(directory: Path) -> List[Path]:
    """Generate list of Apollo PDFs from directory"""
    return sorted(
        [item for item in directory.expanduser().iterdir() if item.match("AP*.pdf")]
    )


def get_rgb_value(filter_name: str) -> tuple[int, int, int]:
    with open(Path(HEX_LOCATION).expanduser(), "r") as f:
        file = f.read()
        vars = chompjs.parse_js_object(file)

    if filter_name == "AP1050":
        # This one doesn't have a value, but it's diffusion so white
        hex_str = "ffffff"
    else:
        hex_str = vars[filter_name]["hex"].replace("#", "")

    rgb = tuple(int(hex_str[i : i + 2], 16) for i in (0, 2, 4))
    return rgb


def extract_boxes(pdf) -> Optional[ApolloBoxes]:
    """
    The back page has 17 visual boxes, each of which has a filled box without stroke,
        and a stroke box without fill.
    We only care about the fill boxes to get an idea of which is selected: the
        selected box will have a non-stroking color of (0, 0, 0) = black.
    The location of the boxes vary from filter to filter so the location is
        dynamically determined per page.
    """

    # Get all filled rectangles
    filled_boxes = [x for x in pdf.pages[1].rects if x["stroke"] is True]
    if len(filled_boxes) == 0:
        return None

    # Determine vertical positions
    y_vals = filter_similar_values([int(x["y0"]) for x in filled_boxes])
    assert len(y_vals) == 5

    # The boundaries are halfway between rows
    # This is a list from bottom to top of the PDF
    y_boundaries = determine_boundaries(y_vals)

    # Get x-vals of the topmost row for saturation bounds
    saturation_x_vals = sorted(
        [int(x["x0"]) for x in filled_boxes if x["y0"] > y_boundaries[-1]]
    )
    assert len(saturation_x_vals) == 5
    saturation_boundaries = determine_boundaries(saturation_x_vals)

    # Get x-vals of the bottom-most row for interaction bounds
    interaction_x_vals = sorted(
        [int(x["x0"]) for x in filled_boxes if x["y0"] < y_boundaries[0]]
    )
    assert len(interaction_x_vals) == 3
    interaction_boundaries = determine_boundaries(interaction_x_vals)

    # Find boxes that have a black fill, i.e. are checked
    checked_boxes = [x for x in filled_boxes if x["non_stroking_color"] == (0, 0, 0)]
    assert len(checked_boxes) == 5

    # The saturation boxes are the top-most boxes
    sat_boxes = [x for x in checked_boxes if x["y0"] > y_boundaries[-1]]
    assert len(sat_boxes) == 1
    sat_box = sat_boxes[0]

    if sat_box["x0"] <= saturation_boundaries[0]:
        saturation = "Very Light"
    elif sat_box["x0"] <= saturation_boundaries[1]:
        saturation = "Light"
    elif sat_box["x0"] <= saturation_boundaries[2]:
        saturation = "Medium"
    elif sat_box["x0"] <= saturation_boundaries[3]:
        saturation = "Deep"
    elif sat_box["x0"] > saturation_boundaries[3]:
        saturation = "Very Deep"
    else:
        # Shouldn't get here
        raise ValueError("Confusing saturation value!")

    interaction = {}
    for interaction_color in ["RED", "BLUE", "GREEN", "YELLOW"]:
        if interaction_color == "RED":
            interaction_box = filter_y_range(
                checked_boxes, y_boundaries[-1], y_boundaries[-2]
            )
        elif interaction_color == "BLUE":
            interaction_box = filter_y_range(
                checked_boxes, y_boundaries[-2], y_boundaries[-3]
            )
        elif interaction_color == "GREEN":
            interaction_box = filter_y_range(
                checked_boxes, y_boundaries[-3], y_boundaries[-4]
            )
        else:
            interaction_box = filter_y_range(checked_boxes, y_boundaries[-4], 0)

        if interaction_box["x0"] <= interaction_boundaries[0]:
            interaction[interaction_color] = "Good"
        elif interaction_box["x0"] <= interaction_boundaries[1]:
            interaction[interaction_color] = "Neutral"
        elif interaction_box["x0"] > interaction_boundaries[1]:
            interaction[interaction_color] = "Poor"
        else:
            # Shouldn't get here
            raise ValueError("Confusing saturation value!")

    return ApolloBoxes(
        saturation=saturation,
        interaction_red=interaction["RED"],
        interaction_blue=interaction["BLUE"],
        interaction_green=interaction["GREEN"],
        interaction_yellow=interaction["YELLOW"],
    )


def get_text_from_page(page) -> List[str]:
    page_text_raw = page.extract_text()
    page_text_clean = page_text_raw.replace("\u201c", '"')
    page_text_clean = page_text_clean.replace("\u201d", '"')
    page_text_clean = page_text_clean.replace("\u2018", "'")
    page_text_clean = page_text_clean.replace("\u2019", "'")
    return page_text_clean.split("\n")


def extract_text(pdf: Path) -> ApolloFilter:
    reader = pdfplumber.open(pdf)

    front_page = get_text_from_page(reader.pages[0])
    back_page = get_text_from_page(reader.pages[1])

    # First line of front is the filter ID
    filter_id = front_page[0]

    # Color name is the next two lines
    name = front_page[1] + " " + front_page[2]

    if "%T" in front_page[-2]:
        # Transmission is second to last line
        transmission = float(front_page[-2].split(" ")[2]) / 100
        conversion = None
    else:
        # For CTO/B/S colors, it lists a conversion value instead of a transmission value
        conversion = " ".join(front_page[3:-1])
        transmission = None

    color_desc_index = [
        idx
        for idx, s in enumerate(back_page)
        if "Color Description" in s or "Note" in s
    ][0]
    if "Note" in back_page[color_desc_index]:
        color_description = None
    else:
        color_description = back_page[color_desc_index + 1]

        # The first letter of some words get seperated
        if color_description[1] == " ":
            color_description = color_description.replace(" ", "", 1)

    # The filter description is between two headers
    desc_index = [idx for idx, s in enumerate(back_page) if "Possible Uses" in s][0]
    description = ""
    for line in back_page[desc_index + 1 : color_desc_index]:

        # Maintain proper spacing between words/sentences
        if line[-1] != " ":
            description += line + " "
        else:
            description += line

    # Oops, sometimes we add a double space
    description = description.replace("  ", " ")

    # Make sure we end in a period
    description = description.strip()
    if description[-1] != ".":
        description += "."

    logger.debug("%s (%s): %s", name, filter_id, description)
    if transmission is not None:
        logger.debug("%s, T = %f", color_description, transmission)
    else:
        logger.debug("%s, %s", color_description, conversion)

    boxes = extract_boxes(reader)
    # extract_sds(reader)
    rgb = get_rgb_value(filter_id)

    return ApolloFilter(
        filter_id=filter_id,
        name=name,
        transmission=transmission,
        conversion=conversion,
        color_description=color_description,
        description=description,
        boxes=boxes,
        rgb=rgb,
    )


def extract_sds(pdf):
    # Get plot only
    graph_box = [x for x in pdf.pages[0].rects if x["width"] > 40][0]

    GRAPH_MARGIN = 0.5
    cropped_graph = pdf.pages[0].crop(
        (
            graph_box["x0"] - GRAPH_MARGIN,
            graph_box["top"] - GRAPH_MARGIN,
            graph_box["x1"] + GRAPH_MARGIN,
            graph_box["bottom"] + GRAPH_MARGIN,
        )
    )

    graph_image = cropped_graph.to_image(resolution=600)
    graph_image.save("test.png")


def main():
    FORMAT = "%(message)s"
    logging.basicConfig(
        level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
    )
    logging.getLogger("pdfplumber").setLevel(logging.INFO)
    logging.getLogger("pdfminer").setLevel(logging.INFO)

    pdf_list = collect_pdfs(Path(PDF_LOCATION))
    logging.info("Collected %s files", len(pdf_list))

    filters = []
    for i in track(pdf_list, description="Parsing swatchbook PDFs..."):
        logger.debug(i)
        filters.append(extract_text(i))

    logger.info("Writing to apollo.json")
    with open("raw/apollo.json", "w") as f:
        f.write(json.dumps(filters, cls=EnhancedJSONEncoder))


if __name__ == "__main__":
    main()
