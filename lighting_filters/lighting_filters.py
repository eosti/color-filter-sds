import json
from typing import Optional, List
import importlib
from pydantic import TypeAdapter
from .types import ColorFilter, FilterModel  # TODO: make these names all the same Color -> Lighting


class LightingFilters(dict):
    def __init__(self, brand_filter: Optional[str | List[str]] = None, dataset_path: Optional[str] = None):
        super().__init__()
        if dataset_path is not None:
            raise NotImplementedError("Can only use internal dataset")

        if dataset_path is None:
            dataset_path = importlib.resources.files('dataset') / 'filters.json'

        with dataset_path.open('r') as f:
            filter_dict = json.loads(f.read())
            model = TypeAdapter(FilterModel).validate_python(filter_dict)

        super().__init__(model.filters)
