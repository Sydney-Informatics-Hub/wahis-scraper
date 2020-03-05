#!/usr/bin/env python
"""Turn downloaded reports into a spreadsheet of data
"""
# Copyright 2020, The University of Sydney
# Please acknowledge the Sydney Informatics Hub for making this data available
# for your research.

import re
import glob
import logging
import os
import argparse

import pandas as pd
from tqdm import tqdm

log = logging.getLogger(__name__)

REPORT_URL = (
    "https://www.oie.int/wahis_2/public/wahid.php/Reviewreport/"
    "Review?reportid={report_id}"
)


def get_details(tables, report_id):
    out = pd.Series()
    disease, _, country = tables[1].loc[0, 1].partition(",")
    out["Disease"] = disease
    out["Country"] = country
    out["Url"] = REPORT_URL.format(report_id=report_id)
    for table in tables:
        if table.loc[0, 0] in {
            "Report type",
            "Source of the outbreak(s) or origin of infection",
            "Measures applied",
        }:
            out = out.append(table.set_index(0)[1])
    out.name = report_id
    return out


def get_outbreaks(tables, report_id, country):
    outbreaks = []

    for outbreak_table, species_table in zip(tables, tables[1:]):
        if not hasattr(outbreak_table.loc[0, 0], "replace"):
            continue
        match = re.match("^Outbreak ([0-9]+)", outbreak_table.loc[0, 0])
        if match is None:
            continue
        assert species_table.loc[0, 0] == "Species"
        outbreak_table = outbreak_table.copy()
        species_table = species_table.copy()

        outbreak_table.loc[0, 0] = "Location"
        outbreak_table = outbreak_table.set_index(0)[1]
        outbreak_table.Location = f"{outbreak_table.Location}, {country}"

        del outbreak_table["Affected animals"]
        species_table.columns = species_table.loc[0]
        species_table = species_table.iloc[1:].infer_objects()
        species_table.insert(0, "Outbreak #", int(match.group(1)))
        outbreaks.append(species_table.assign(**outbreak_table))

    if not outbreaks:
        return pd.DataFrame()
    outbreaks = pd.concat(outbreaks, sort=False)
    outbreaks.insert(0, "Report ID", report_id)
    return outbreaks.set_index(["Report ID", "Outbreak #"])


def get_tests(tables, report_id):
    test_table = None
    for table in tables:
        if table.loc[0, 0] == "Laboratory name and type":
            test_table = table.copy()
            test_table.columns = test_table.loc[0]
            test_table = test_table.iloc[1:].infer_objects()

    if test_table is None:
        return pd.DataFrame()

    test_table.insert(0, "Report ID", report_id)
    return (
        test_table.reset_index()
        .rename(columns={"index": "Test #"})
        .set_index(["Report ID", "Test #"])
    )


def process_report(path):
    log.debug(f"Reading {path}")
    try:
        tables = pd.read_html(path, encoding="utf-8")
    except ValueError:
        if "Application Error" in open(path).read():
            log.warning(f"Report in {path} was affected by an " "Application Error")
            return pd.Series(), pd.DataFrame(), pd.DataFrame()
        raise
    report_id = re.findall("[0-9]+", path)[0]
    details = get_details(tables, report_id)
    outbreaks = get_outbreaks(tables, report_id, details.Country)
    tests = get_tests(tables, report_id)
    for df in [outbreaks, tests]:
        df.insert(0, "Disease", details.Disease)
        df.insert(1, "Country", details.Country)
        df.insert(2, "Report date", details["Report date"])
    return details, outbreaks, tests


def process_reports(paths):
    reports, outbreaks, tests = zip(
        *(process_report(path) for path in tqdm(paths, desc="Extracting"))
    )
    reports = pd.concat(reports, axis=1, sort=False).transpose()
    reports = reports.dropna(how="all", axis=0)  # failed reports
    reports.index.name = "Report ID"
    outbreaks = pd.concat(outbreaks, sort=False)
    tests = pd.concat(tests, sort=False)
    return reports, outbreaks, tests


def dump(out_path, reports, outbreaks, tests):
    writer = pd.ExcelWriter(out_path)
    reports.to_excel(writer, sheet_name="reports")
    outbreaks.to_excel(writer, sheet_name="outbreaks", merge_cells=False)
    tests.to_excel(writer, sheet_name="tests", merge_cells=False)
    writer.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out_dir")
    ap.add_argument(
        "--glob",
        default="*.html",
        help="Glob pattern for reports to load from out_dir. Default: *.html",
    )
    ap.add_argument(
        "--xlsx-name",
        default="reports.xlsx",
        help="Filename to dump spreadsheet. Default: reports.xlsx",
    )
    args = ap.parse_args()

    results = process_reports(glob.glob(os.path.join(args.out_dir, args.glob)))
    xlsx_path = os.path.join(args.out_dir, args.xlsx_name)
    log.info(f"Writing output to {xlsx_path}")
    dump(xlsx_path, *results)


if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s : %(message)s", level=logging.INFO
    )
    main()
