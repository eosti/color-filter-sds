# color-filter-sds
A collection of spectral distribution (SD) datasets for lighting color filters. 

I couldn't find a easy-to-use dataset of filters, so I compiled one myself!
For now, the dataset exists in `data/all_filters.json`, but I plan to eventually make other ways of accessing the data such as a Python library. 

For each manufacturer, there is a set of 'raw' data in `generators/raw` that represents anything I could pull from the sources available. 
These have some more specialty measurements such as stops and mired shift that only exist for certain filters and as such don't show up in the main dataset. 
The raw data is not as uniformly manicured as the main dataset, so some additional poking around may be needed. 
These raw datasets are what the main dataset is derived from, so the data should agree with each other. 

# Sources
All filter data is owned by their respective companies, I did not measure or characterize any filter myself. 
All data here is publicly available, provided by the manufacturer to the end user. 
For more granular data or for commercial licensing, please contact the manufacturer. 
I do not work for nor am affiliated with any filter manufacturer, so please don't ask me about it!

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
- Create Python module that integrates with the `colour-science` module
- Try graphical curve fitting to get a smart-extrapolation of SD graphs

