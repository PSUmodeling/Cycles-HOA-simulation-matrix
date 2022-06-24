#!/usr/bin/env python3

import pandas
import numpy as np
import os

CROPLAND_FILE = "data/HOACropland.csv"
OUTPUT_FILE = "data/HOACropland_new.csv"

countries = [
    "Kenya",
    "Ethiopia",
    "South Sudan",
    "Sudan",
    "Uganda",
    "Somalia",
    "Eritrea",
    "Djibouti",
]

crops = [
    "Maize",
    "Sorghum",
    "Cassava",
]

pds = [
    "15",
    "46",
    "74",
    "105",
    "135",
    "166",
    "196",
    "227",
    "258",
    "288",
    "319",
    "345",
]

def reference_pd(row):
    '''
    Find the date with maximum 5-month moving average yield to be the reference planting date.
    '''
    length = 12
    half_window = 2

    max_yield = -999
    ref_day = -999
    for m in range(length):
        # Adjust to avoid using indices larger than 11
        m = m - length if m >= length - half_window else m

        yield_ma = row[np.r_[m - half_window:m + half_window + 1]].mean()
        if yield_ma > max_yield:
            max_yield = yield_ma
            ref_day = row.index[m]

    return (max_yield, ref_day)

# Open cropland file
cropland_df = pandas.read_csv(CROPLAND_FILE)
cropland_df.fillna("NaN", inplace=True)     # Fill NaN values incase 'admin3' does not exist

for crop in crops:
    # Create an empty data frame to contain all countries/planting dates
    pd_df = pandas.DataFrame()
    for country in countries:
        print (country, crop)
        first = 1
        for pd in pds:
            # Read output files
            output_df = pandas.read_csv("outputs/%s.%s.%s.csv" % (country, crop, pd), usecols=range(1,6))
            output_df.fillna("NaN", inplace=True)   # Fill NaN values incase 'admin3' does not exist

            # Calculate mean grain yield over all simulation years
            output_df = pandas.DataFrame(output_df.groupby(["country", "admin1", "admin2", "admin3"]).mean())

            # Rename the column to planting date, which can be merged into pd_df
            output_df.rename(columns={"grain_yield": str(pd)}, inplace=True)

            # Add all planting dates to one data frame
            if first == 1:
                _result_df = output_df
                first = 0
            else:
                _result_df = _result_df.merge(output_df, how="inner", on=["country", "admin1", "admin2", "admin3"])

        # Combine all results
        pd_df = pd_df.append(_result_df)

    # Find reference planting dates and yields
    pd_df[["grain_yield","pd"]] = pd_df.apply(lambda row: pandas.Series(reference_pd(row)), axis=1)

    # Remove yields of each month
    pd_df.drop(columns=pds, inplace=True)

    # Rename pd and grain_yield columns to each crop
    crop = crop.strip().lower().replace(" ", "_")
    pd_df.rename(columns={"pd": "%s_pd" %(crop), "grain_yield": "%s_grain_yield" %(crop)}, inplace=True)

    # Add planting dates and yields to cropland data
    cropland_df = cropland_df.merge(pd_df, how="inner", on=["country", "admin1", "admin2", "admin3"])

# Write to output file
cropland_df.replace("NaN", "", regex=True, inplace=True)

cropland_df.to_csv(OUTPUT_FILE, index=False)
