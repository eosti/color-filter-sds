# color-filter-sds
A collection of data for lighting color filters. 

# Usage
The complete dataset exists in `dataset/filters.json`.
For usage with other programs, the `json_schema.json` contains an annotated description of how the dataset is organized. 

There also exists a nicer-for-humans XLSX file at `data/filters.xlsx` with the following limitations:

- No SD data, but will show if there is data available
- CIE coords are displayed as a (x, y, Y) string which is going to suck to do math on
- No formatting

For each manufacturer, there is also a set of 'raw' data in `generators/raw` that represents anything I could pull from the sources available. 
These have some more specialty measurements such as stops and mired shift that only exist for certain filters and as such don't show up in the main dataset. 
The raw data is not as uniformly manicured as the main dataset, so some additional poking around may be needed. 

## Python
For usage in Python applications, you can install the package with `pip install lighting_filters`.
Usage is straightforward: 

```python
from lighting_filters import LightingFilters

filters = LightingFilters()
print(filters["R54"])
```

Examples of how the library can be used are found in `examples/`.

# Sources
All filter data is owned by their respective companies, I did not measure or characterize any filter myself. 
All data here is publicly available, provided by the manufacturer to the end user. 
For more granular data or for commercial licensing, please contact the manufacturer. 

To play around with the generators in `generators/`, install prerequisites using `poetry install --with=generators`.

## Apollo
The Apollo data is pulled from a set of swatchbook PDFs kindly provided to me by Apollo -- this repo does not contain these PDFs, but the parsing code is available. 
If any discrepancies are noticed, I can manually compare and provide the swatchbook pages if needed. 

The Apollo RGB values are pulled from an archived version of their [Gel Converter tool](https://web.archive.org/web/20220818010004/https://www.apollodesign.net/gel-color-filter-converter).

Apollo no longer manufactures gel as of 2020ish, but old stock may still be floating around. 
And besides, it'd be a shame to lose the delightful color names.

## Lee
The Lee data is scraped directly from the [Lee Filters](https://leefilters.com/) website. 

## Rosco
The existing Rosco data is scraped from [Rosco myColor](https://us.rosco.com/en/mycolor).

# Future Work
- Finish Rosco dataset: the spectral distribution values exist in PDF form but that's hard to parse. 
- Integrate `lighting_filters` with `colour-science`
- Try graphical curve fitting to get a smart-extrapolation of SD graphs
- Clean up XLSX export

