import sys
from gui.gui import MainWindow, Run

if __name__ == "__main__":
    mainWindow = MainWindow()    
    sys.exit(
        Run(
            sys.argv,
            mainWindow
            )
        )