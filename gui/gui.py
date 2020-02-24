from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QWizard, QWizardPage, QPushButton, QLineEdit, QFileDialog, QMessageBox, QTreeView, QPlainTextEdit, QWidget, QLabel, QComboBox, QTableView
from PySide2.QtGui import QStandardItemModel, QStandardItem
from PySide2.QtCore import QFile, Slot, QSize
from .resizeStackWidget import ResizeStackWidget

from data.dataModel import NamedNetContainer, TargetNetContainer
import os

from .dataSinkAndSource import *

class ConditionalWizard(QWizard):
    def __init__(self, *argc, **argv):
        super().__init__(*argc, **argv)
        self.currentIdChanged.connect(self.onPageChanged)
        self.__last_idx = 0
        self.__callback = None

    @Slot()
    def onPageChanged(self, page_idx):
        if self.__callback is not None:
            if self.__last_idx < page_idx:  # changed to the next page
                if self.__callback(self.__last_idx) is False:
                    self.back()
                    return
        self.__last_idx = page_idx
            
    def accept(self):
        if self.__callback is not None:
            if self.__callback(-1) is False:
                return
        super().accept()

    def registerCallback(self, callback):
        self.__callback = callback

class ConfigEntry:
    def __init__(self, source_rsw_idx, sink_rsw_idx, target_rsw_idx, source_input, sink_input, target_input):
        self.source_rsw_idx = source_rsw_idx
        self.sink_rsw_idx = sink_rsw_idx
        self.target_rsw_idx = target_rsw_idx
        self.source_input = source_input
        self.sink_input = sink_input
        self.target_input = target_input

class MainWindow:
    def __init__(self):
        self.__dataModel = None
        self.__operation_result = None

    def buildGui(self):
        ui_file_loader = QUiLoader()
        ui_file_loader.registerCustomWidget(ResizeStackWidget)
        ui_file_loader.registerCustomWidget(ConditionalWizard)

        main_ui_file = QFile("ui/main_wizard.ui")
        main_ui_file.open(QFile.ReadOnly)
        self._window = ui_file_loader.load(main_ui_file)
        main_ui_file.close()

        #
        def fc(type, name):
            return self._window.findChild(type, name)
        def fc_l(name):
            return fc(QLineEdit, name)
        def fc_b(name):
            return fc(QPushButton, name)
        def fc_cb(name):
            return fc(QComboBox, name)
        def fc_p(name):
            l = fc_l(name+"_lineEdit")
            b = fc_b(name+"_pushButton")
            if l is None:
                raise Exception("lineEdit {}_lineEdit not found".format(name))
            if b is None:
                raise Exception("pushButton {}_pushButton not found".format(name))
            return [l, b]

        # page 0

        self.__operation_cb = fc_cb("operation_comboBox")
        self.__operation_cb.currentIndexChanged.connect(self.onOperationSelect)

        self.__source_rsw = fc(ResizeStackWidget, "source_stackedWidget")
        self.__sink_rsw = fc(ResizeStackWidget, "sink_stackedWidget")

        self.__datasource_stm = STM32CubeMX_DataSource(self._window, fc_p("source_stm") )
        self.__datasource_eagle = AutodeskEagle_DataSource(self._window, fc_p("source_eagle_sch"), fc_p("source_eagle_ic") )

        self.__datasink_stm = STM32CubeMX_DataSink(self._window, fc_p("sink_stm") )
        self.__datasink_eagle = AutodeskEagle_DataSink(self._window, fc_p("sink_eagle_sch"), fc_p("sink_eagle_brd"), fc_p("sink_eagle_ic") )

        self._window.registerCallback(self.onPageChanged)

        # page 1

        self.__changelog_model = QStandardItemModel()
        self.__error_model = QStandardItemModel()

        self.__changelog_tableView = fc(QTableView, "changelog_tableView")
        self.__changelog_tableView.setModel(self.__changelog_model)
        self.__error_tableView = fc(QTableView, "error_tableView")
        self.__error_tableView.setModel(self.__error_model)

        # page 2

        self.__target_rsw = fc(ResizeStackWidget,"target_stackedWidget")

        self.__datatarget_stm = STM32CubeMX_DataTarget(self._window, fc_p("target_stm") )
        self.__datatarget_eagle = AutodeskEagle_DataTarget(self._window, fc_p("target_eagle_sch"), fc_p("target_eagle_brd") )


        self.config_by_idx = {
        # operation idx
            # stm => eagle
            0: ConfigEntry(
                source_rsw_idx = 0,
                sink_rsw_idx = 1,
                target_rsw_idx = 1,
                source_input = self.__datasource_stm,
                sink_input = self.__datasink_eagle,
                target_input = self.__datatarget_eagle
            ),
            # eagle => stm
            1: ConfigEntry(
                source_rsw_idx = 1,
                sink_rsw_idx = 0,
                target_rsw_idx = 0,
                source_input = self.__datasource_eagle,
                sink_input = self.__datasink_stm,
                target_input = self.__datatarget_stm
            )            
        }

        self.__operation_cb.setCurrentIndex(0)
        self.onOperationSelect(0)

    def show(self):
        self._window.show()

    @Slot()
    def onOperationSelect(self, idx):
        # clean settings and entries
        for dm in [self.__datasource_stm, self.__datasource_eagle, self.__datasink_stm, self.__datasink_eagle, self.__datatarget_stm, self.__datatarget_eagle]:
            dm.clear()

        config = self.config_by_idx[idx]

        self.__source_rsw.setCurrentIndex(  config.source_rsw_idx )
        self.__sink_rsw.setCurrentIndex(    config.sink_rsw_idx   )
        self.__target_rsw.setCurrentIndex(  config.target_rsw_idx )

    def onPageChanged(self, page_idx):
        if page_idx == -1:
            return self.onWriteFiles()
        if page_idx == 0:
            return self.onDataSelected()
        if page_idx == 1:
            return True
        return False

    def onDataSelected(self):
        config = self.config_by_idx[self.__operation_cb.currentIndex()]
        
        source  = config.source_input
        sink    = config.sink_input
        target  = config.target_input

        source.load()
        sink.load()

        target.copyInputFrom(sink)

        if source.isLoaded() == False or sink.isLoaded() == False:
            return False

        source_model = source.getModel()
        sink_model = sink.getModel()

        tnn = TargetNetContainer.fromNNC(sink_model, source_model)
        self.__operation_result = sink.apply(tnn)
        
        # display log
        self.__changelog_model.clear()
        self.__changelog_model.setHorizontalHeaderLabels(["Pin", "From", "To"])
        for entry in self.__operation_result.log:
            self.__changelog_model.appendRow(
                [
                    QStandardItem(str(entry.name)), 
                    QStandardItem(str(entry.net)),
                    QStandardItem(str(entry.new_net))
                ]
            )
        
        # display errors
        self.__error_model.clear()
        self.__error_model.setHorizontalHeaderLabels(["Type", "Message"])        
        for line in self.__operation_result.errors:
            self.__error_model.appendRow([QStandardItem("Error"), QStandardItem(line)])
        for line in self.__operation_result.warnings:
            self.__error_model.appendRow([QStandardItem("Warning"), QStandardItem(line)])

        self.__changelog_tableView.resizeColumnsToContents()
        self.__error_tableView.resizeColumnsToContents()

        return True

    def onWriteFiles(self):
        if self.__operation_result is None:
            return False

        config = self.config_by_idx[self.__operation_cb.currentIndex()]

        config.target_input.write(self.__operation_result)

def Run(argv, widget):
    app = QApplication(argv)
    widget.buildGui()
    widget.show()
    return app.exec_()