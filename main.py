import sys
from gui.gui import MainWindow, Run

def test():
    # from data.loader import AutodeskEagle_SCH_Loader as AESL

    # with open("C:\\_Daten\\sonntag_env\\Schaltung_und_Layout\\MAS_3\\MAS3DZ\\MAS3DZ_MoBo\\v3\\MAS3_DZ_v31.sch") as f:
    #     print(AESL.getModel(f.read(), "IC1"))

    from data.loader import STM32CubeMX_CSV_Loader as Loader

    with open("./cube.csv") as f:
        print(Loader.getModel(f.read()))

if __name__ == "__main__":
    # test()
    # exit(0)

    mainWindow = MainWindow()    
    sys.exit(
        Run(
            sys.argv,
            mainWindow
            )
        )