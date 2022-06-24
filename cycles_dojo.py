#!/usr/bin/env python3

import argparse
import glob
import os
import pandas as pd
import shutil
import subprocess
import zipfile

RESOURCES_FILE = "data/HOAResources.csv"
CROPLAND_FILE = "data/HOACropland.csv"
CYCLES_RUN_DIR = "bin/cycles/"
TMP_DIR = "tmp"
OUTPUT_FILE = "outputs/cycles_results.csv"
CROPS_FILE = "data/crops-horn-of-africa.crop"
SOIL_WEATHER_DIR = "../clouseau/data/soil_weather"

def run_cycles(params):
    cropland_df = pd.read_csv(CROPLAND_FILE)
    cropland_df.set_index(["country", "admin1", "admin2", "admin3"], inplace=True)

    df = pd.read_csv(RESOURCES_FILE)
    df.set_index(["country", "admin1", "admin2", "admin3"], inplace=True)
    country_soil_points = df.loc[params["country"]]

    os.makedirs("tmp", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

    # Run Cycles for all soil points in the country
    # - TODO: Should run in parallel
    first = True
    for index, point in country_soil_points.iterrows():

        # Get the crop fractional area for this region
        cropland_row = cropland_df.loc[params["country"], index[0], index[1], index[2]]
        crop_fractional_area = cropland_row[params["crop_name"].lower()+"_fractional_area"]

        # Get the input/output files
        inputfile = point["filename"]
        sim = f"{inputfile.replace('.soil_weather.zip', '')}.{params['crop_name']}.{params['start_planting_day']}"
        season_file = f"{TMP_DIR}/{sim}.season"
        summary_file = f"{TMP_DIR}/{sim}.summary"

        # create Cycles input folder and copy base files
        cmd = "rm -fr input* output"
        subprocess.run(cmd, shell=True)

        os.makedirs("input", exist_ok=True)
        #copy the crop file to the input directory
        shutil.copy(CROPS_FILE, "input/")

        #extract the zipfile into the input directory
        with zipfile.ZipFile(f"{SOIL_WEATHER_DIR}/{inputfile}", "r") as zip_ref:
            zip_ref.extractall("input")

        #obtain the file of weather and soil file
        weather = os.path.basename(glob.glob("input/*.weather")[0])
        soil = os.path.basename(glob.glob("input/*.soil")[0])

        # run cycles baseline
        cmd = [
            "python3",
            f"{CYCLES_RUN_DIR}/cycles-wrapper.py",
            "--start-year",
            params["start_year"],
            "--end-year",
            params["end_year"],
            "--baseline",
            "True",
            "--crop",
            params["crop_name"],
            "--start-planting-date",
            params["start_planting_day"],
            "--end-planting-date",
            "0",
            "--fertilizer-rate",
            "50",
            "--weed-fraction",
            params["weed_fraction"],
            "--forcing",
            "False",
            "--reinit-file",
            "input/cycles.reinit",
            "--weather-file",
            weather,
            os.path.basename(CROPS_FILE),
            soil,
        ]
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"Error")

        ### moving and renaming output data
        shutil.move("output/cycles-run/season.txt", season_file)
        shutil.move("output/cycles-run/summary.txt", summary_file)

        # Load the output file
        exdf = get_dataframe_for_execution_result(season_file, index, params,
            ["grain_yield", "cum._n_stress", "actual_tr", "potential_tr"])

        # Filter/Modify/Add Columns
        exdf["crop_production"] = exdf["grain_yield"] * crop_fractional_area
        exdf["water_stress"] = 1.0 - exdf["actual_tr"] / exdf["potential_tr"]
        exdf = exdf.rename(columns={"cum._n_stress": "nitrogen_stress"})
        exdf = exdf.drop(["actual_tr", "potential_tr"], axis=1)

        # Write output
        if first:
            exdf.to_csv(OUTPUT_FILE, index=False)
            first = False
        else:
            exdf.to_csv(OUTPUT_FILE, mode="a", header=False, index=False)


def load_execution_result(outputloc):
    df = pd.read_csv(outputloc, sep="\t", header=0, skiprows=[1], skipinitialspace=True)
    df = df.rename(columns=lambda x: x.strip().lower().replace(" ", "_"))
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    return df


def get_dataframe_for_execution_result(season_file, index, params, result_fields):
    df = load_execution_result(season_file)

    # Fetch feature values
    ndf = df.filter(result_fields, axis=1)

    # Insert timestamp
    ndf.insert(0, "date", df["date"]) #.values.astype(np.int64) // 10 ** 9)

    # Insert geospatial details
    ndf.insert(1, "country", params["country"])
    ndf.insert(2, "admin1", index[0] if index[0] else None)
    ndf.insert(3, "admin2", index[1] if index[1] else None)
    ndf.insert(4, "admin3", index[2] if index[2] else None)

    return ndf


def _main():
    parser = argparse.ArgumentParser(
        description="Cycles execution for a country"
    )
    parser.add_argument("--country", dest="country", default="Kenya", help="Country name")
    parser.add_argument("--crop-name", dest="crop_name", default="Maize", help="Crop name")
    parser.add_argument("--start-year", dest="start_year", default="2000", help="Simulation start year")
    parser.add_argument("--end-year", dest="end_year", default="2020", help="Simulation end year")
    parser.add_argument("--start-planting-day", dest="start_planting_day", default="103", help="Start planting date")
    parser.add_argument("--fertilizer-rate", dest="fertilizer_rate", default="50.00", help="Fertilizer rate")
    parser.add_argument("--weed-fraction", dest="weed_fraction", default="0.2", help="Weed fraction")
    args = parser.parse_args()
    run_cycles(vars(args))

    os.rename(OUTPUT_FILE, "outputs/%s.%s.%s.csv" % (args.country, args.crop_name, args.start_planting_day))


if __name__ == "__main__":
    _main()