"""Pull filter information from Lee's website"""

import dataclasses
import json
import logging
import re
from typing import Optional
from unicodedata import numeric

import requests
from bs4 import BeautifulSoup
from rich.logging import RichHandler
from rich.progress import track

logger = logging.getLogger(__name__)

LEE_BASE_URL = "https://leefilters.com/lighting/colour-effect-lighting-filters/"


class FilterParsingError(Exception):
    """Exception for expected issues when scraping"""


@dataclasses.dataclass
class SDVals:
    """Stores specific spectral data"""

    color_temperature: int
    transmission_y: float
    absorption: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None
    stop: Optional[float] = None
    mired_shift: Optional[float] = None


@dataclasses.dataclass
class LeeFilter:
    """General dataclass for Lee data"""

    filter_id: str
    name: str
    description: Optional[str]
    rgb: tuple[int, int, int]
    daylight_vals: SDVals
    tungsten_vals: Optional[SDVals]
    sd: Optional[dict]
    url: str


class EnhancedJSONEncoder(json.JSONEncoder):
    """Helper for packing dataclasses"""

    def default(self, o):
        """Unpacks a dataclass into a dict"""
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)


def unicode_fraction_decoder(value: str) -> float:
    """Converts a mixed or normal fraction using Unicode fractions to a float
    Source: https://stackoverflow.com/a/50264056"""
    if len(value) == 1:
        # If just one character, then it's a fraction
        v = numeric(value)
    elif value[-1].isdigit():
        # normal number, ending in [0-9]
        v = float(value)
    else:
        # Assume the last character is a vulgar fraction
        v = float(value[:-1]) + numeric(value[-1])

    return v


def get_available_filters():
    """Pulls all available filters from Lee's site"""
    page = requests.get(LEE_BASE_URL)
    soup = BeautifulSoup(page.content, "html.parser")

    all_colors = soup.find_all("li", class_="colours-list__colour")
    ret = []
    for c in all_colors:
        ret.append(c.find("a")["href"])

    logger.info("Collected %i colors", len(ret))
    return ret


def parse_transmission(temp):
    """Parses the transmission info box"""
    data = {}
    data["color_temperature"] = int(temp.find("p").text.split(" ")[2].replace("K", ""))
    for i in temp.find_all("li"):
        key = i.find(class_="spec-list__spec").text.strip()
        value = i.find(class_="spec-list__value").text

        # Discard > or < characters because those ain't numbers
        value = value.replace("<", "").replace(">", "").strip()

        if value == "-":
            pass
        elif re.search("[\u2150-\u215E\u00BC-\u00BE]", value) is not None:
            # Unicode fraction needs to be converted
            data[key.lower().replace(" ", "_")] = unicode_fraction_decoder(value)
        else:
            data[key.lower().replace(" ", "_")] = float(value)

        # There's a few filters with empty information for some reason.
        # Discard any data without transmission Y data
        if "transmission_y" not in data:
            return None

    return SDVals(**data)


def parse_filter(url: str):
    """Pulls all info for a specific filter"""
    page = requests.get(url)
    soup = BeautifulSoup(page.content, "html.parser")

    h1 = soup.find(class_="page-header__text").find("h1").text
    try:
        # Most filters are given as a number, these are LXXX filters
        number = int(h1.split(" ", 1)[0])
        filter_id = f"L{number:03}"
    except ValueError:
        # But some specialty filters don't follow this scheme
        filter_id = h1.split(" ", 1)[0]

    # This replaces a – (minus), not a - (hyphen)
    name = h1.split(" ", 1)[1].replace("–", "").strip()

    try:
        desc = soup.find(class_="page-header__colour-desc").find("p").text.strip()
    except AttributeError:
        desc = None

    logging.debug("%s (%s): %s", filter_id, name, desc)

    header_style = soup.find(class_="page-header__colour")["style"]
    header_hex = header_style.split("#")[1].replace(";", "")
    rgb = tuple(int(header_hex[i : i + 2], 16) for i in (0, 2, 4))

    sd = {}
    if soup.find("circle", class_="tooltip") is None:
        logger.info("No SD found for %s", h1)
        sd = None
    else:
        for point in soup.find_all("circle", class_="tooltip"):
            pointsoup = BeautifulSoup(point["title"], "html.parser")
            sd[int(pointsoup.find("span").text)] = (
                float(pointsoup.find("b").text) * 0.01
            )

    tungsten_vals = None
    daylight_vals = None

    if soup.find(class_="colour__transmissions") is None:
        logger.info("No SD data found for %s", h1)
    else:
        for temperature in soup.find(class_="colour__transmissions").find_all(
            "li", recursive=False
        ):
            temperature_data = parse_transmission(temperature)
            if temperature_data is None:
                continue
            if temperature_data.color_temperature == 3200:
                tungsten_vals = temperature_data
            elif temperature_data.color_temperature == 6774:
                daylight_vals = temperature_data
            else:
                raise ValueError

    return LeeFilter(
        filter_id=filter_id,
        name=name,
        description=desc,
        url=url,
        tungsten_vals=tungsten_vals,
        daylight_vals=daylight_vals,
        sd=sd,
        rgb=rgb,
    )


def main():
    """Scrapes all filters from Lee's website"""
    FORMAT = "%(message)s"
    logging.basicConfig(
        level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
    )

    filter_urls = get_available_filters()
    filters = []
    for i in track(filter_urls, description="Scraping filter information..."):
        try:
            filters.append(parse_filter(i))
        except FilterParsingError as e:
            logger.warning("Unable to parse %s", i)
            logger.warning(e)

    logger.info("Writing to lee.json")
    with open("raw/lee.json", "w") as f:
        f.write(json.dumps(filters, cls=EnhancedJSONEncoder))


if __name__ == "__main__":
    main()
