# WAHIS Scraper

These command-line tools scrape data from the OIE World Organisation for Animal Health data portal, WAHIS.

It will get outbreak reports and follow-up reports for all countries for a specified disease.

It generates a spreadsheet listing each report, each outbreak and each lab test.

## Setup with Anaconda/Miniconda

In this directory, install the requirements by executing:

```
conda env create
```

Then activate the environment with:

```
conda activate wahis-scraper
```

The Google Chrome browser should be installed.

## Usage

Note that the oie.net server is slow, and these processes may take a long time.
Stopping the download process and restarting should largely resume where it left off.

Run with:

```
python download.py <output_directory> -d <terrestrial_disease_id> -y <min_year>-<max_year>
```

This will deposit files in the specified output directory.

Then:

```
python tabulate.py <output_directory>
```

This will read all reports deposited in the output directory, and write back `reports.xlsx` summarising the reports.

## Developed by the Sydney Informatics Hub

This tool was developed by the Sydney Informatics Hub, a core research facility of The University of Sydney.

If using this scraper and its data output in your research, please acknowledge the Sydney Informatics Hub in publications.

         /  /\        ___          /__/\   
        /  /:/_      /  /\         \  \:\  
       /  /:/ /\    /  /:/          \__\:\ 
      /  /:/ /::\  /__/::\      ___ /  /::\
     /__/:/ /:/\:\ \__\/\:\__  /__/\  /:/\:\
    \  \:\/:/~/:/    \  \:\/\ \  \:\/:/__\/
      \  \::/ /:/      \__\::/  \  \::/    
       \__\/ /:/       /__/:/    \  \:\    
         /__/:/ please \__\/      \  \:\   
         \__\/ acknowledge your use\__\/   

