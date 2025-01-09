"""Exports JSON dataset into a Pythonic format"""

import importlib
import json
import logging
from pathlib import Path
from typing import List, Optional

from pydantic import TypeAdapter

from .typedef import FilterModel

logger = logging.getLogger(__name__)


class LightingFilters(dict):
    """dict that is preloaded with data from the JSON dataset"""

    def __init__(
        self,
        brand_filter: Optional[str | List[str]] = None,
        dataset_path: Optional[str] = None,
    ):
        """Loads dict with data in JSON, optionally filters for certain brands"""

        if dataset_path is None:
            dataset_file = importlib.resources.files("dataset") / "filters.json"
        else:
            dataset_file = Path(dataset_path)

        logger.debug("Loading filters from %s", dataset_file)

        with dataset_file.open("r") as f:
            filter_dict = json.loads(f.read())
            model = TypeAdapter(FilterModel).validate_python(filter_dict)

        all_filters = model.filters
        if len(all_filters) == 0:
            raise RuntimeError("No filters loaded")

        if brand_filter is None:
            filtered_filters = all_filters
        elif isinstance(brand_filter, str):
            filtered_filters = {
                k: v for k, v in all_filters.items() if v.brand == brand_filter
            }
        elif isinstance(brand_filter, list):
            filtered_filters = {}
            for brand in brand_filter:
                filtered_filters.update(
                    {k: v for k, v in all_filters.items() if v.brand == brand}
                )
        else:
            raise TypeError("Brand filter must be str or list of strs")

        if len(filtered_filters) == 0:
            raise RuntimeError(f"No filters matched brand '{brand_filter}'")

        logger.info("Loaded %s filters", len(filtered_filters))

        super().__init__(filtered_filters)

    # TODO: make this class unwritable after init
