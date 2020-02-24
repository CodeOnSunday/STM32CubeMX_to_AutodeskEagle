import sys
from cx_Freeze import setup, Executable

setup(  name = "STM32CubeMX to Eagle",
        version = "1.1",
        description = "",
        options = {
            "build_exe": {
                "packages": ["os"],
                "excludes": ["tkinter"],
                "include_files": [
                    (r"ui\main_wizard.ui", r"ui\main_wizard.ui"),
                    (r"ui\select_ic.ui", r"ui\select_ic.ui"),
                    (r"settings\alternative_pin_names.csv", r"settings\alternative_pin_names.csv")
                ]
            }
        },
        executables = [
            Executable("main.py", base="Win32GUI")
        ])