from PySide2.QtWidgets import QFileDialog, QMessageBox
from PySide2.QtCore import QFile, Slot, QSize

import os

from .selectIC import openSelectICDialog

from data.loader import *
KNOWN_FILE_EXT_LOADER = {
    ".ioc": STM32CubeMX_Loader,
    ".csv": STM32CubeMX_CSV_Loader,
    ".sch": AutodeskEagle_SCH_Loader,
    ".brd": None
}

class ValidationFailed(Exception):
    @staticmethod
    def fileExistsValidation(path):
        if not os.path.exists(path):
            raise ValidationFailed()

class LineEditWithButton:
    def __init__(self, lineEdit, button, handler):
        self.__line_edit = lineEdit
        self.__handler = handler
        self.__button = button
        self.__button.clicked.connect(self.onButton)

    @Slot()
    def onButton(self):
        self.__handler(self)

    def getValue(self):
        return self.__line_edit.text()

    def setValue(self, value):
        self.__line_edit.setText(value)
        return self

def generateOFD(master, title, filter):
    def f(manager):
        path, _ = QFileDialog.getOpenFileName(master, title, manager.getValue(), filter)
        if len(path) > 0:
            manager.setValue(path)
    return f

def generateNotImplemented():
    def f(_):
        raise NotImplementedError()
    return f

class DataManager:
    def validate(self):
        raise NotImplementedError()

    def load(self):
        raise NotImplementedError()

    def isLoaded(self):
        raise NotImplementedError()

    def clear(self):
        raise NotImplementedError()

class DataSource(DataManager):
    def getModel(self):
        raise NotImplementedError()

class DataSink(DataManager):
    def getTargetModel(self, data_model):
        raise NotImplementedError()

class STM32CubeMX_DataSource(DataSource):
    def __init__(self, window, source):
        self.__source = LineEditWithButton(
            source[0], 
            source[1], 
            generateOFD(
                window, 
                "Select data source", 
                "STM32CubeMX (*.ioc *.csv)"
            )
        )
        self.__loaded = False
        self.__window = window

    def validate(self):
        ValidationFailed.fileExistsValidation(self.__source.getValue())
        
    def isLoaded(self):
        return self.__loaded

    def clear(self):
        self.__loaded = False
        self.__source.setValue("")

    def load(self):
        try:
            self.validate()
        except ValidationFailed:
            self.__loaded = False
            QMessageBox.critical(self.__window, "File not found", "STM32CubeMX file \"{}\" can't be found.".format(self.__source.getValue()))
            return

        if self.isLoaded():
            return

        path = self.__source.getValue()
        with open(path) as f:
            self.__file_content = f.read()
            _, self.__file_ext = os.path.splitext(self.__source.getValue())
            if self.__file_ext not in KNOWN_FILE_EXT_LOADER:
                QMessageBox.critical(self.__window, "File extension unknown", "Can't handle files with extension \"{}\".".format(self.__file_ext))
                self.__loaded = False
                return
            self.__loaded = True

    def getModel(self):
        if not self.isLoaded():
            return

        try:
            return KNOWN_FILE_EXT_LOADER[self.__file_ext].getModel(self.__file_content)
        except FileFormatUnknown:
            QMessageBox.critical(self.__window, "File format unknown", "The file \"{}\" seams not to be a valid STM32CubeMX file.".format(self.__source.getValue()))
            return

class STM32CubeMX_DataSink(DataSink):
    def __init__(self, window, sink):
        self.__source = LineEditWithButton(
            sink[0], 
            sink[1], 
            generateOFD(
                window, 
                "Select data sink", 
                "STM32CubeMX (*.ioc *.csv)"
            )
        )
        self.__loaded = False
        self.__window = window

    def validate(self):
        ValidationFailed.fileExistsValidation(self.__source.getValue())
        
    def isLoaded(self):
        return self.__loaded

    def clear(self):
        self.__loaded = False
        self.__source.setValue("")

    def load(self):
        try:
            self.validate()
        except ValidationFailed:
            self.__loaded = False
            QMessageBox.critical(self.__window, "File not found", "STM32CubeMX file \"{}\" can't be found.".format(self.__source.getValue()))
            return

        if self.isLoaded():
            return

        path = self.__source.getValue()
        with open(path) as f:
            self.__file_content = f.read()
            _, self.__file_ext = os.path.splitext(self.__source.getValue())
            if self.__file_ext not in KNOWN_FILE_EXT_LOADER:
                QMessageBox.critical(self.__window, "File extension unknown", "Can't handle files with extension \"{}\".".format(self.__file_ext))
                self.__loaded = False
                return
            self.__loaded = True

    def getModel(self):
        if not self.isLoaded():
            return

        try:
            return KNOWN_FILE_EXT_LOADER[self.__file_ext].getModel(self.__file_content, self.__ic.getValue())
        except FileFormatUnknown:
            QMessageBox.critical(self.__window, "File format unknown", "The file \"{}\" seams not to be a valid STM32CubeMX file.".format(self.__source.getValue()))
            return

class AutodeskEagle_DataSource(DataSource):
    def __init__(self, window, schematic, ic):
        self.__schematic = LineEditWithButton(
            schematic[0], 
            schematic[1], 
            generateOFD(
                window, 
                "Select source schematic", 
                "Autodesk Eagle (*.sch)"
            )
        )
        self.__ic = LineEditWithButton(
            ic[0], 
            ic[1], 
            self.openSelectICDialog
        )
        self.__loaded = False
        self.__window = window

    def validate(self):
        ValidationFailed.fileExistsValidation(self.__schematic.getValue())

    def load(self):
        if self.isLoaded():
            return
        
        try:
            self.validate()
        except ValidationFailed:
            self.__loaded = False
            QMessageBox.critical(self.__window, "File not found", "Autodesk Eagle schematic \"{}\" can't be found.".format(self.__schematic.getValue()))
            return

        path = self.__schematic.getValue()
        with open(path) as f:
            self.__file_content = f.read()
            _, self.__file_ext = os.path.splitext(self.__schematic.getValue())
            if self.__file_ext not in KNOWN_FILE_EXT_LOADER:
                QMessageBox.critical(self.__window, "File extension unknown", "Can't handle files with extension \"{}\".".format(self.__file_ext))
                self.__loaded = False
                return
            self.__loaded = True

    def isLoaded(self):
        return self.__loaded

    def openSelectICDialog(self, manager):
        self.load()

        if not self.isLoaded():
            return

        try: 
            ic_list = KNOWN_FILE_EXT_LOADER[self.__file_ext].getICList(self.__file_content)
        except FileFormatUnknown:
            QMessageBox.critical(self.__window, "File format unknown", "The file \"{}\" seams not to be a valid Autodesk Eagle schematic.".format(self.__schematic.getValue()))
            return

        accepted, ic = openSelectICDialog(ic_list)
        if accepted:
            self.__ic.setValue(ic)

    def clear(self):
        self.__loaded = False
        self.__schematic.setValue("")
        self.__ic.setValue("")

    def getModel(self):
        if not self.isLoaded():
            return

        try:
            return KNOWN_FILE_EXT_LOADER[self.__file_ext].getModel(self.__file_content, self.__ic.getValue())
        except FileFormatUnknown:
            QMessageBox.critical(self.__window, "File format unknown", "The file \"{}\" seams not to be a valid Autodesk Eagle schematic.".format(self.__schematic.getValue()))
            return

class AutodeskEagle_DataSink(DataSink):
    def __init__(self, window, schematic, board, ic):
        self.__schematic = LineEditWithButton(
            schematic[0], 
            schematic[1], 
            generateOFD(
                window, 
                "Select sink schematic", 
                "Autodesk Eagle (*.sch)"
            )
        )
        self.__board = LineEditWithButton(
            board[0], 
            board[1], 
            generateOFD(
                window, 
                "Select sink board", 
                "Autodesk Eagle (*.brd)"
            )
        )
        self.__ic = LineEditWithButton(
            ic[0], 
            ic[1], 
            self.openSelectICDialog
        )
        self.__loaded = False
        self.__window = window

    def validate(self):
        ValidationFailed.fileExistsValidation(self.__schematic.getValue())
        ValidationFailed.fileExistsValidation(self.__board.getValue())

    def load(self):
        if self.isLoaded():
            return

        try:
            self.validate()
        except ValidationFailed:
            self.__loaded = False
            QMessageBox.critical(self.__window, "File not found", "One of the selected files can't be found.")
            return

        path = self.__schematic.getValue()
        with open(path) as f:
            self.__schematic_content = f.read()
            _, self.__schematic_ext = os.path.splitext(self.__schematic.getValue())
            if self.__schematic_ext not in KNOWN_FILE_EXT_LOADER:
                QMessageBox.critical(self.__window, "File extension unknown", "Can't handle files with extension \"{}\".".format(self.__schematic_ext))
                self.__loaded = False
                return

        path = self.__board.getValue()
        with open(path) as f:
            self.__board_content = f.read()
            _, self.__board_ext = os.path.splitext(self.__board.getValue())
            if self.__board_ext not in KNOWN_FILE_EXT_LOADER:
                QMessageBox.critical(self.__window, "File extension unknown", "Can't handle files with extension \"{}\".".format(self.__board_ext))
                self.__loaded = False
                return
        
        self.__loaded = True

    def isLoaded(self):
        return self.__loaded

    def openSelectICDialog(self, manager):
        self.load()

        if not self.isLoaded():
            return

        try: 
            ic_list = KNOWN_FILE_EXT_LOADER[self.__schematic_ext].getICList(self.__schematic_content)
        except FileFormatUnknown:
            QMessageBox.critical(self.__window, "File format unknown", "The file \"{}\" seams not to be a valid Autodesk Eagle schematic.".format(self.__schematic.getValue()))
            return

        accepted, ic = openSelectICDialog(ic_list)
        if accepted:
            self.__ic.setValue(ic)

    def clear(self):
        raise NotImplementedError()

    def clear(self):
        self.__loaded = False
        self.__schematic.setValue("")
        self.__board.setValue("")
        self.__ic.setValue("")

    def getModel(self):
        if not self.isLoaded():
            return

        try:
            return KNOWN_FILE_EXT_LOADER[self.__schematic_ext].getModel(self.__schematic_content, self.__ic.getValue())
        except FileFormatUnknown:
            QMessageBox.critical(self.__window, "File format unknown", "The file \"{}\" seams not to be a valid Autodesk Eagle schematic.".format(self.__schematic.getValue()))
            return

    def apply(self, target_net_container):
        if not self.isLoaded():
            return

        return KNOWN_FILE_EXT_LOADER[self.__schematic_ext].applyOperation(self.__schematic_content, self.__board_content, self.__ic.getValue(), target_net_container)

        # TODO:
        # try:
        #     return KNOWN_FILE_EXT_LOADER[self.__schematic_ext].applyOperation(self.__schematic_content, self.__board_content, self.__ic.getValue(), target_net_container)
        # except FileFormatUnknown:
        #     QMessageBox.critical(self.__window, "File format unknown", "The file \"{}\" seams not to be a valid Autodesk Eagle schematic.".format(self.__schematic.getValue()))
        #     return
    
