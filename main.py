import sys

from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QApplication, QWizard, QWizardPage, QPushButton, QLineEdit, QFileDialog, QMessageBox, QTreeView, QPlainTextEdit
from PySide2.QtGui import QStandardItem, QStandardItemModel
from PySide2.QtCore import QFile, Slot

import xml.etree.ElementTree as ET
import csv, types

class FileBrowser:
    def __init__(self, title, master, button_name, entry_name, custom_handler = None, open_dialog = True):
        self._title = title
        self._master = master
        self._entry = master.findChild(QLineEdit, entry_name)
        self._ch = custom_handler
        self._open = open_dialog
        master.findChild(QPushButton, button_name).clicked.connect(self.onButtonClick)

    @Slot()
    def onButtonClick(self):
        if self._open:
            path, _ = QFileDialog.getOpenFileName(self._master, self._title, self._entry.text(), "*.*")
        else:
            path, _ = QFileDialog.getSaveFileName(self._master, self._title, self._entry.text(), "*.*")
        if len(path) > 0:
            self.setText(path)
            if self._ch is not None:
                self._ch(path)

    def setText(self, text):
        self._entry.setText(text)

    def getText(self):
        return self._entry.text()

class CubeLine:
    def __init__(self, pin="", net=""):
        self.Pin = pin
        self.Net = net

class NetRegistryEntry:
    def __init__(self, old_name="", tmp_name="", new_name=""):
        self.old_name = old_name
        self.tmp_name = tmp_name
        self.new_name = new_name

class CondWizard(QWizard):
    def __init__(self, *arg, **argv):
        super().__init__(*arg, **argv)
        self._accept_condition = None

    def setCondition(self, cond):
        self._accept_condition = cond

    def accept(self):
        if self._accept_condition is None:
            super().accept()
        elif self._accept_condition():
            super().accept()

class Wizard:
    def __init__(self, ui_filepath):
        self._last_page = 0

        self._eagle_sch_tree = None
        self._eagle_brd_tree = None
        self._ic_model = QStandardItemModel()
        self._cube_defs = []
        
        # ui
        ui_file = QFile(ui_filepath)
        ui_file.open(QFile.ReadOnly)
        loader = QUiLoader()
        loader.registerCustomWidget(CondWizard)
        self._window = loader.load(ui_file)
        ui_file.close()

        self._window.currentIdChanged.connect(self.onPageChanged)        
        self._window.setCondition(self.onAccept)
        self._cube_file_browser = FileBrowser("STM32CubeMX file", self._window, "cube_file_button", "cube_file_textbox")
        self._eagle_sch_target_browser = FileBrowser("Target schematic file", self._window, "eagle_sch_target_button", "eagle_sch_target_textbox", open_dialog=False)
        self._eagle_brd_target_browser = FileBrowser("Target board file", self._window, "eagle_brd_target_button", "eagle_brd_target_textbox", open_dialog=False)
        self._eagle_sch_file_browser = FileBrowser("Eagle schematic file", self._window, "eagle_sch_file_button", "eagle_sch_file_textbox", lambda text: self._eagle_sch_target_browser.setText(text))
        self._eagle_brd_file_browser = FileBrowser("Eagle board file", self._window, "eagle_brd_file_button", "eagle_brd_file_textbox", lambda text: self._eagle_brd_target_browser.setText(text))
        self._window.findChild(QTreeView, "ic_treeView").setModel(self._ic_model)

        self._window.show()

    @Slot()
    def onPageChanged(self, page_id):
        if self._last_page == 0 and page_id == 1:
            if not self.loadFiles():
                self._window.back()
                return
        elif self._last_page == 1 and page_id == 2:            
            if not self.process():
                self._window.back()
                return 

        self._last_page = page_id

    def onAccept(self):   
        # write result to schematic file
        try:
            sch_file = open(self._eagle_sch_target_browser.getText(), "w")
        except OSError as e:
            QMessageBox.critical(self._window, "Can't open target file", str(e))
            return False

        # write result to board file
        try:
            brd_file = open(self._eagle_brd_target_browser.getText(), "w")
        except OSError as e:
            QMessageBox.critical(self._window, "Can't open target file", str(e))
            return False

        ET.ElementTree(self._eagle_sch_tree).write(sch_file, encoding="unicode")
        sch_file.close()
        ET.ElementTree(self._eagle_brd_tree).write(brd_file, encoding="unicode")
        brd_file.close()

        return True

    def loadFiles(self):
        # check if files exist and are accessible

        cube_content = None
        try:
            cube_file = open(self._cube_file_browser.getText(), "r")
            
            self._cube_defs = []
            reader = csv.DictReader(cube_file)
            for row in reader:
                if "Name" not in row or "Label" not in row:
                    QMessageBox.critical(self._window, "Wrong format", "The STM32CubeMX file format can't be validated.")
                    return False
                if len(row["Label"]) > 0:   
                    pin_name = row["Name"]
                    for sc in ["/", "-"]:   # if the name of the pin contains a special character, use only the leading part
                        pin_name = pin_name.split("/")[0] 

                    ALLOWED_CHAR = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-+")
                    net_list = list(row["Label"].upper())
                    net_label = ""
                    if net_list[0] in ALLOWED_CHAR:
                        if net_list[0] == "_":  # if the first character is a _, replace it with a !
                            net_label += "!"
                        else:
                            net_label += net_list[0]
                    else:
                        net_label += "_"

                    for c in net_list[1:]:
                        if c in ALLOWED_CHAR:
                            net_label += c
                        else:
                            net_label += "_"
                    if len(net_label) > 0:
                        self._cube_defs.append(CubeLine(pin_name, net_label))

            cube_file.close()
        except OSError as e:
            QMessageBox.critical(self._window, "Can't open STM32CubeMX file", str(e))
            return False

        try:
            eagle_file = open(self._eagle_sch_file_browser.getText(), "r")
            self._eagle_sch_tree = ET.parse(eagle_file).getroot()
            eagle_file.close()
        except OSError as e:
            QMessageBox.critical(self._window, "Can't open Eagle file", str(e))
            return False

        try:
            eagle_file = open(self._eagle_brd_file_browser.getText(), "r")
            self._eagle_brd_tree = ET.parse(eagle_file).getroot()
            eagle_file.close()
        except OSError as e:
            QMessageBox.critical(self._window, "Can't open Eagle file", str(e))
            return False

        # generate data model of ic list
        self._ic_model.clear()
        mr = self._ic_model.invisibleRootItem()
        for idx, sheet in enumerate(self._eagle_sch_tree.findall(".//sheet")):
            sheet_item = QStandardItem("Sheet {}".format(idx+1))
            ic_list = []
            for idx2, ics in enumerate(sheet.findall(".//instance")):
                if "part" in ics.attrib:
                    if ics.attrib["part"] not in ic_list:
                        ic_list.append(ics.attrib["part"])
            ic_list.sort()
            for ic in ic_list:
                sheet_item.appendRow(QStandardItem(ic))
            mr.appendRow(sheet_item)

        return True

    def process(self):
        if self._eagle_sch_tree is None:
            QMessageBox.critical(self._window, "No Eagle schematic loaded.", "No Eagle schematic loaded.")
            return False
        if  self._eagle_brd_tree is None:
            QMessageBox.critical(self._window, "No Eagle board loaded.", "No Eagle board loaded.")
            return False

        tv = self._window.findChild(QTreeView, "ic_treeView")
        sel_idx = tv.selectedIndexes()        
        if len(sel_idx) != 1:
            QMessageBox.critical(self._window, "Select one item.", "Please select exactly one IC.")
            return False

        ic_name = self._ic_model.itemFromIndex(sel_idx[0]).text()

        if self._eagle_sch_tree.find(".//sheet//instance[@part='{}']".format(ic_name)) is None:            
            QMessageBox.critical(self._window, "Error.", "Can't find the IC \"{}\" in schematic. Please select another.".format(ic_name))
            return False

        log_text = ""
        error_text = ""

        net_registry = []
        black_list = {}

        # find nets wich should not be updated but have a name conflict
        new_def_list = []
        for line in self._cube_defs:
            net = self._eagle_sch_tree.find(".//net[@name='{net}']".format(net=line.Net))
            if net is not None: # found a net with the same name as a target
                pin = self._eagle_sch_tree.find(".//net[@name='{net}']//pinref[@part='{ic}']".format(net=line.Net, ic=ic_name))
                if pin is None: # if the net is not connected to the ic, it will not be updated and so is a conflict
                    error_text += "The net {net} will be ignored, cause it is not connected to the target ic.\r\n".format(net=line.Net)
                else:
                    new_def_list.append(line)
            else:
                    new_def_list.append(line)
        self._cube_defs = new_def_list                    

        # find all nets which should be updated
        for line in self._cube_defs:
            if line.Net not in black_list:
                # find current net name
                query = ".//pinref[@part='{ic}'][@pin='{pin}']/../..".format(ic=ic_name, pin=line.Pin)
                result = self._eagle_sch_tree.find(query)
                if result is None:
                    error_text += "Can't find net to change into {net} for pin {pin} of ic {ic}.\r\n".format(ic=ic_name, pin=line.Pin, net=line.Net)                
                else:
                    old_net_name = result.attrib["name"]
                    if old_net_name != line.Net: # if the new name equals the old one, we have nothing to do
                        net_registry.append(NetRegistryEntry(old_net_name, "", line.Net))
                black_list[line.Net] = 1
            else:
                black_list[line.Net] += 1

        net_registry = list( filter(lambda x: black_list[x.new_name] == 1, net_registry) )
        log_text += "Found {} nets to rename.\r\n".format(len(net_registry))
        for net in black_list:
            if black_list[net] > 1:
                error_text += "Ignored net {net} cause it has {count} duplication.\r\n".format(net=net, count=black_list[net]-1)                

        ## schematic
        # assign a tmp name to the nets
        for idx, entry in enumerate(net_registry):
            tmp_name = "cube2eagle_tmp_name_{}".format(idx) # associate the temporary name with the old and new one
            net_registry[idx].tmp_name = tmp_name
            result = self._eagle_sch_tree.findall(".//net[@name='{net}']".format(net=entry.old_name))
            for net in result:  # rename all nets
                net.set("name", tmp_name)
        
        # rename nets from tmp name to target name
        for idx, entry in enumerate(net_registry):
            log_text += "Renamed net {oldname} into {newname}.\r\n".format(oldname=entry.old_name, newname=entry.new_name)
            result = self._eagle_sch_tree.findall(".//net[@name='{net}']".format(net=entry.tmp_name))
            for net in result:
                net.set("name", entry.new_name)

        ## board
        # assign a tmp name to the nets
        for idx, entry in enumerate(net_registry):
            result = self._eagle_brd_tree.findall(".//signal[@name='{net}']".format(net=entry.old_name))
            for net in result:  # rename all nets
                net.set("name", entry.tmp_name)
        
        # rename nets from tmp name to target name
        for idx, entry in enumerate(net_registry):
            result = self._eagle_brd_tree.findall(".//signal[@name='{net}']".format(net=entry.tmp_name))
            for net in result:
                net.set("name", entry.new_name)
        

        self._window.findChild(QPlainTextEdit, "changed_plainTextEdit").setPlainText(log_text)
        self._window.findChild(QPlainTextEdit, "error_plainTextEdit").setPlainText(error_text)

        return True


if __name__ == "__main__":
    app = QApplication(sys.argv)

    w = Wizard("wizard.ui")

    sys.exit(app.exec_())