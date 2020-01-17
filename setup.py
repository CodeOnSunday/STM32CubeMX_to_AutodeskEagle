import sys
from cx_Freeze import setup, Executable

setup(  name = "STM32CubeMX to Eagle",
        version = "1.1",
        description = "",
        options = {
            "build_exe": {
                "packages": ["os"],
                "excludes": ["tkinter"],
                "include_files": ["wizard.ui"]
            }
        },
        executables = [
            Executable("main.py", base="Win32GUI")
        ])