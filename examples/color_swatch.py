from lighting_filters import LightingFilters
from argparse import ArgumentParser
import logging
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def main():
    logging.basicConfig(level=logging.WARNING)

    parser = ArgumentParser(
        prog="color_swatch.py",
        description="Creates a color swatch from a given lighting filter."
    )
    parser.add_argument(
        "filter_id",
        help="ID of lighting filter (ex. R54, L201, G990)",
    )
    parser.add_argument(
        "--font",
        default="Arial",
        help="Font in which the filter ID is printed"
    )
    parser.add_argument(
        "--size",
        default=400,
        type=int,
        help="Edge length of image in pixels"
    )

    args = parser.parse_args()

    filters = LightingFilters()

    try:
        selected_filter = filters[args.filter_id]
    except KeyError:
        logger.error("Filter %s not found", args.filter_id)
        exit(1)

    # User-set values (generally larger value = smaller)
    text_padding_scalar = 18
    between_lines_padding_scalar = 80
    filter_font_scalar = 7
    desc_font_scalar = 11
    contrast_threshold = 50

    # Calculated sizes
    text_padding = args.size / text_padding_scalar
    between_lines_padding = args.size / between_lines_padding_scalar
    filter_font_size = args.size / filter_font_scalar  # Equals text height
    desc_font_size = args.size / desc_font_scalar  # Equals text height

    # Adaptive font color
    filter_rgb = selected_filter.rgb
    logger.debug("%s has perceived lightness of %f", filter_rgb.to_hex(), filter_rgb.perceived_lightness())

    if filter_rgb.perceived_lightness() > contrast_threshold:
        # If color is too bright, font color is black
        font_color = (20, 20, 20)
    else:
        # Default font color is a white
        font_color = (0xdd, 0xdd, 0xdd)

    filter_font = ImageFont.truetype(f"{args.font}.ttf", filter_font_size)
    desc_font = ImageFont.truetype(f"{args.font}.ttf", desc_font_size)

    img = Image.new('RGB', (args.size, args.size), selected_filter.rgb.as_tuple())
    d = ImageDraw.Draw(img)
    d.text((text_padding, args.size - text_padding - between_lines_padding - filter_font_size - desc_font_size), args.filter_id, font=filter_font, fill=font_color)
    d.text((text_padding, args.size - text_padding - desc_font_size), selected_filter.name, font=desc_font, fill=font_color)
    img.show()


if __name__ == "__main__":
    main()
