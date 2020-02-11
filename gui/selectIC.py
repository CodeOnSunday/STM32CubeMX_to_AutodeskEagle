from PySide2.QtUiTools import QUiLoader
from PySide2.QtCore import QFile, Slot, QSize, QStringListModel
from PySide2.QtWidgets import QListView


class SelectICDialog:
    def __init__(self, ic_list):
        ic_list.sort()

        self.__ic_model = QStringListModel(ic_list)
        self.__accepted = False
        self.__selectedIC = None
    
    def buildGUI(self):
        ui_file_loader = QUiLoader()
        dialog_ui_file = QFile("ui/select_ic.ui")
        dialog_ui_file.open(QFile.ReadOnly)
        self._window = ui_file_loader.load(dialog_ui_file)
        dialog_ui_file.close()

        self.__lv = self._window.findChild(QListView, "listView")
        self.__lv.setModel(self.__ic_model)
        self.__lv.activated.connect(self.onActivated)
        self._window.accepted.connect(self.onAccepted)

    def getResult(self):
        return self.__accepted, self.__selectedIC

    def show(self):
        self._window.exec_()

    @Slot()
    def onActivated(self, idx):
        self._window.accept()

    @Slot()
    def onAccepted(self):
        idx_list = self.__lv.selectedIndexes()
        if len(idx_list) == 1:
            self.__accepted = True
            self.__selectedIC = self.__ic_model.data(idx_list[0])

def openSelectICDialog(ic_list):
    sid = SelectICDialog(ic_list)
    sid.buildGUI()
    sid.show()
    return sid.getResult()