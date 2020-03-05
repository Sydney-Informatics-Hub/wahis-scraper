#!/usr/bin/env python
"""Turn downloaded reports into a spreadsheet of data
"""
# Copyright 2020, The University of Sydney
# Please acknowledge the Sydney Informatics Hub for making this data available
# for your research.


import requests
import time
import os
import re
import logging
import argparse

from tqdm import tqdm
import pandas as pd
from selenium import webdriver
from selenium.webdriver.support.ui import Select


log = logging.getLogger(__name__)
MAX_RETRIES = 5
START_URL = "https://www.oie.int/wahis_2/public/wahid.php/Diseaseinformation/Immsummary"
REPORT_URL = "https://www.oie.int/wahis_2/public/wahid.php/Reviewreport/Review?reportid={report_id}"


def get_summary_urls(disease_id, min_year, max_year, disease_type="terrestrial"):
    log.info("Opening start page")
    driver = webdriver.Chrome()
    driver.get(START_URL)

    select = Select(driver.find_element_by_id(f"disease_id_{disease_type}"))
    select.select_by_value(str(disease_id))
    time.sleep(10)

    summary_urls = []
    for year in tqdm(range(min_year, max_year + 1), desc="Getting years"):
        select = Select(driver.find_element_by_id("year"))
        select.select_by_value(str(year))
        time.sleep(10)
        for elem in driver.find_elements_by_class_name("outbreakdetails"):
            country = (
                elem.find_element_by_class_name("outbreak_country").text.strip()
                or country
            )
            url = elem.find_element_by_link_text("Summary").get_attribute("href")
            summary_urls.append({"year": year, "country": country, "url": url})

    driver.close()

    return pd.DataFrame(summary_urls)


def get_report_ids(out_dir, summary_urls):
    all_report_ids = []
    for url in tqdm(sorted(set(summary_urls.url)), desc="Getting report IDs"):
        summary_id = re.search("reportid=([0-9]+)", url).group(1)
        summary_path = os.path.join(out_dir, f"summary_{summary_id}.lst")

        if os.path.exists(summary_path):
            all_report_ids.extend([x.strip() for x in open(summary_path)])
            continue

        time.sleep(0.5)
        resp = requests.get(url)
        html = resp.text
        report_ids = re.findall(r"'(\d+)'\)\">Full report</a>", html)
        with open(summary_path, "w") as f:
            print("\n".join(report_ids), file=f)
        all_report_ids.extend(report_ids)
    return all_report_ids


def get_reports(out_dir, report_ids):
    skipped = retrieved = 0
    for report_id in tqdm(report_ids, desc="Getting reports"):
        path = os.path.join(out_dir, f"{report_id}.html")
        if os.path.exists(path):
            log.debug(f"Skipping {path}")
            skipped += 1
            continue
        log.debug(f"Downloading {path}")
        time.sleep(0.5)
        url = REPORT_URL.format(report_id=report_id)
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                report_resp = requests.get(url, timeout=30)
            except Exception:
                if attempt == MAX_RETRIES:
                    raise
            break
        open(path, "w").write(report_resp.text)
        retrieved += 1
    log.info(f"Retrieved {retrieved} reports; Already saved: {skipped}")


def parse_year_range(s):
    min_year, max_year = s.split("-", 1)
    return int(min_year), int(max_year)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out_dir")
    ap.add_argument(
        "-d",
        "--disease-id",
        type=int,
        required=True,
        help="Terrestrial diseased ID. ASF is 12",
    )
    ap.add_argument(
        "-y",
        "--year-range",
        required=True,
        type=parse_year_range,
        help="Range of years, e.g. 2007-2016",
    )
    ap.add_argument("--resume", default=False, action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(args.out_dir):
        os.mkdir(args.out_dir)
    summary_urls_path = os.path.join(args.out_dir, "summary_urls.xlsx")
    if args.resume:
        summary_urls = pd.read_excel(summary_urls_path, index_col=0)
    elif os.path.exists(summary_urls_path):
        ap.error(
            f"Refusing to overwrite {summary_urls_path}. "
            "Use --resume if you want to use what's there."
        )
    else:
        summary_urls = get_summary_urls(args.disease_id, *args.year_range)
        summary_urls.to_excel(summary_urls_path)
    report_ids = get_report_ids(args.out_dir, summary_urls)
    get_reports(args.out_dir, sorted(report_ids))


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s : %(message)s", level=logging.INFO
    )
    main()
