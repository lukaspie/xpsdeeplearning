# -*- coding: utf-8 -*-
"""
Created on Thu Jul 23 17:44:57 2020

@author: Mark
"""
import json

# import xlsxwriter
import re
import numpy as np
from copy import copy

from .vamas import VamasHeader, Block

#%%
class TextWriter:
    def __init__(self):
        pass

    def write(self, data, filename):
        lines = self.build_lines(data)

        with open(str(filename), "w") as file:
            for line in lines:
                file.writelines(line["header_line"] + "\n")
                for data_line in line["data_lines"]:
                    file.writelines(str(data_line) + "\n")

    def build_lines(self, data):
        lines = []
        for d in data:
            header_line = d["spectrum_type"] + " " + d["group_name"]
            data_lines = [
                str(np.round(x, 3)) + " " + str(y)
                for x, y in zip(d["data"]["x"], d["data"]["y0"])
            ]
            lines.append(
                {"header_line": header_line, "data_lines": data_lines}
            )

        return lines


class VamasWriter:
    def __init__(self):
        self.normalize = 0

    def write(self, data, filename):
        """ This method converts a nested dictionary into vamas format
        and writes it to a vamas file.
        """
        self.filename = filename
        self.num_spectra = 0
        self.file_path = ""
        self.millenium = 2000
        self.header_lines = 15
        self.spectra = []
        self.blocks = []
        self.sourceAnalyzerAngle = "56.5"
        self.vamas_header = VamasHeader()
        self.scans_averaged = 0
        self.loops_averaged = 0
        self.count_type = "Counts per Second"
        self.blocks_counter = 0
        self.blocks = []
        for spec in data:
            block = Block()
            block.sampleID = spec["group_name"]

            block.blockID = spec["spectrum_type"]
            block.noCommentLines = 10
            block.commentLines = (
                "Casa Info Follows\n0\n0\n0\n0\n"
                + "none"
                + "\nGroup: "
                + "none"
                + "\nAnalyzer Lens: "
                + "none"
                + "\nAnalyzer Slit: "
                + "none"
                + "\nScan Mode: "
                + "none"
            )
            block.expVarValue = 0
            split_string = re.split(r"(\d)", spec["spectrum_type"])
            species = split_string[0]
            transition = ""
            for i in split_string[1:]:
                transition += i
            block.speciesLabel = species
            block.transitionLabel = transition
            block.noScans = spec["scans"]
            if len(spec["date"].split(" ")) == 3:
                date, time, zone = spec["date"].split(" ")
            elif len(spec["date"].split(" ")) == 2:
                date, time = spec["date"].split(" ")
            if len(date.split("/")) == 3:
                block.month, block.day, block.year = date.split("/")
            elif len(date.split("-")) == 3:
                block.month, block.day, block.year = date.split("-")
            if len(block.year) == 2:
                block.year = int(block.year) + self.millenium
            block.hour, block.minute, block.second = time.split(":")
            block.noHrsInAdvanceOfGMT = "0"  # zone.strip('UTC')
            setting = spec["settings"]
            block.technique = setting["analysis_method"]
            block.sourceLabel = setting["source_label"]
            block.sourceEnergy = setting["excitation_energy"]
            block.sourceAnalyzerAngle = self.sourceAnalyzerAngle
            block.analyzerMode = "FAT"
            block.resolution = setting["pass_energy"]
            block.workFunction = setting["workfunction"]
            block.dwellTime = setting["dwell_time"]

            y_units = setting["y_units"]
            if y_units == "Counts per Second":
                y = [
                    i * float(block.dwellTime) * float(block.noScans)
                    for i in spec["data"]["y0"]
                ]
            else:
                y = [i for i in spec["data"]["y0"]]
            if self.normalize != 0:
                norm = self.normalize
                y = [
                    spec["data"]["y0"][i]
                    / spec["data"]["y" + str(norm)][i]
                    for i in range(len(spec["data"]["y0"]))
                ]
            x_units = setting["x_units"]
            if (x_units == "Binding Energy") & (
                setting["scan_mode"] != "FixedEnergies"
            ):
                block.abscissaStart = str(
                    float(block.sourceEnergy)
                    - float(setting["binding_energy"])
                )
            else:
                block.abscissaStart = spec["data"]["x"][0]
            block.abscissaStep = abs(
                spec["data"]["x"][1] - spec["data"]["x"][0]
            )

            if "nr_values" not in setting.keys():
                nr_values = len(spec["data"]["y0"])
                block.numOrdValues = str(
                    int(nr_values * int(block.noAdditionalParams))
                )
            else:
                block.numOrdValues = str(
                    int(setting["nr_values"])
                    * int(block.noAdditionalParams)
                )
            block.minOrdValue1 = min(spec["data"]["y0"])
            block.maxOrdValue1 = max(spec["data"]["y0"])
            block.minOrdValue2 = 1
            block.maxOrdValue2 = 1
            for i in y:
                block.dataString += str(i) + "\n1\n"
            block.dataString = block.dataString[:-1]
            self.blocks += [copy(block)]
            block.dataString = ""
        self.num_spectra = len(self.blocks)
        self.vamas_header.noBlocks = self.num_spectra

        with open(str(filename), "w") as file:
            for item in self.vamas_header.__dict__:
                file.writelines(
                    str(self.vamas_header.__dict__[item]) + "\n"
                )
            for block in self.blocks:
                for item in block.__dict__:
                    file.writelines(str(block.__dict__[item]) + "\n")
            file.writelines("end of experiment")
            file.close()
