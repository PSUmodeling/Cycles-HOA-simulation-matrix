#!/usr/bin/env python3
"""Cycles Executor."""

import argparse
import csv
import logging
import os
import shutil
import subprocess
import sys
from string import Template

log = logging.getLogger()

global basedir
basedir = os.path.dirname(__file__)

def _generate_inputs(
        prefix,
        start_year,
        end_year,
        baseline,
        crop,
        start_planting_date,
        end_planting_date,
        fertilizer_rate,
        weed_fraction,
        forcing,
        weather_file,
        reinit_file,
        crop_file,
        soil_file,
        **kwargs):

    global basedir
    ctrl_file = "cycles-run.ctrl"
    op_file = "cycles-run.operation"

    # process CTRL file
    with open(f"{basedir}/template.ctrl") as t_ctrl_file:
        src = Template(t_ctrl_file.read())
        ctrl_data = {
            "start_year": start_year,
            "end_year": end_year,
            "rotation_size": 1,
            "crop_file": crop_file,
            "operation_file": op_file,
            "soil_file": soil_file,
            "weather_file": weather_file,
            "reinit": 0 if baseline == "True" else 1,
        }
        result = src.substitute(ctrl_data)
        with open("./input/" + ctrl_file, "w") as f:
            f.write(result)

    # process Operation file
    operation_contents = ""
    with open(f"{basedir}/template.operation") as t_op_file:
        src = Template(t_op_file.read())
        op_data = {
            "year_count": 1,
            "crop_name": crop,
            "fertilization_date": int(start_planting_date) - 10,
            "fertilization_rate": fertilizer_rate,
            "start_planting_date": start_planting_date,
            "end_planting_date": end_planting_date,
            "tillage_date": int(start_planting_date) + 20,
        }
        result = src.substitute(op_data)
        operation_contents += result + "\n"

        # handling weeds
        if float(weed_fraction) > 0:
            with open(f"{basedir}/template-weed.operation") as t_wd_file:
                wd_src = Template(t_wd_file.read())
                wd_data = {
                    "year_count": 1,
                    "weed_planting_date": int(start_planting_date) + 7,
                    "weed_fraction": weed_fraction
                }
                wd_result = wd_src.substitute(wd_data)
                operation_contents += wd_result + "\n"

    # writing operations file
    with open("./input/" + op_file, "w") as f:
        f.write(operation_contents)


def _launch(prefix, baseline, **kwargs):
    cmd = f"{basedir}/Cycles -s cycles-run" if baseline == "True" else f"{basedir}/Cycles cycles-run"
    print(cmd)
    try:
        output = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, shell=True, universal_newlines=True)
    except subprocess.CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.output)
        exit(1)
    else:
        print("Output: \n{}\n".format(output))


def _main():
    parser = argparse.ArgumentParser(
        description="Cycles executor."
    )
    parser.add_argument("--start-year", dest="start_year", default=2000, help="Simulation start year")
    parser.add_argument("--end-year", dest="end_year", default=2017, help="Simulation end year")
    parser.add_argument("-b", "--baseline", dest="baseline", default=False, help="Whether this is a baseline execution")
    parser.add_argument("-c", "--crop", dest="crop", default="Maize", help="Crop name")
    parser.add_argument("-s", "--start-planting-date", dest="start_planting_date", default=100, help="Start planting date")
    parser.add_argument("-e", "--end-planting-date", dest="end_planting_date", default=0, help="End planting date") # Changed default to 0, which changes to -999 below, and implies automatic end planting date
    parser.add_argument("-n", "--fertilizer-rate", dest="fertilizer_rate", default=0.00, help="Fertilizer rate")
    parser.add_argument("-w", "--weed-fraction", dest="weed_fraction", default=0.0, help="Weed fraction")
    parser.add_argument("-f", "--forcing", dest="forcing", default=False, help="Whether it uses forcing data from PIHM")
    parser.add_argument("-l", "--weather-file", dest="weather_file", default=None, help="Weather file")
    parser.add_argument("-r", "--reinit-file", dest="reinit_file", default=None, help="Cycles reinitialization file")
    parser.add_argument("crop_file", help="crops file")
    parser.add_argument("soil_file", help="Soil file")
    args = parser.parse_args()

    # setting prefix
    prefix = "_baseline" if args.baseline == "True" else ""

    if args.end_planting_date == 0:
        args.end_planting_date = -999

    _generate_inputs(prefix, **vars(args))
    _launch(prefix, **vars(args))


if __name__ == "__main__":
    _main()
