import os
import csv
from .dataModel import NamedNetContainer, TargetNetContainer, OperationContext
import xml.etree.ElementTree as ET

class FileFormatUnknown(Exception):
    pass

class PinAlias:
    register = None

    def __init__(self):
        filename = "../settings/alternative_pin_names.csv"
        if PinAlias.register is None:
            self.loadData(filename)

    def getIdForAlias(self, alias):
        if alias in PinAlias.register:
            return PinAlias.register[alias]
        return alias

    def loadData(self, filename):
        PinAlias.register = {}
        with open(os.path.dirname(__file__) + "/" + filename) as f:
            reader = csv.reader(f, delimiter=",", quotechar='"')
            for line in reader:
                id_ = line[0]
                for alias in line[1:]:
                    PinAlias.register[alias] = id_

class STM32CubeMX_Loader:
    @staticmethod
    def labelToNetName(label):
        if label == "":
            return ""
        ALLOWED_CHAR = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-+")
        def mask(c):
            c = c.upper()
            if c in ALLOWED_CHAR:
                return c
            return "_"
        label = list((mask(c) for c in label))
        if label[0] == "_":
            label[0] = "!"
        return "".join(label)

class STM32CubeMX_CSV_Loader:
    @staticmethod
    def getModel(file_content):
            reader = csv.DictReader(file_content.split("\n"), delimiter=",", quotechar='"')
            nnc = NamedNetContainer()
            pa = PinAlias()
            for line in reader:
                nnc.addEntry(
                    pa.getIdForAlias(line["Name"]), 
                    STM32CubeMX_Loader.labelToNetName(line["Label"])
                )
            return nnc

class AutodeskEagle_SCH_Loader:
    @staticmethod
    def getXML(file_content):
        if isinstance(file_content, str):
            return ET.fromstring(file_content)
        if isinstance(file_content, ET.Element):
            return file_content
        raise TypeError()

    @staticmethod
    def getICList(file_content):
        xml = AutodeskEagle_SCH_Loader.getXML(file_content)
        result = []
        for idx, value in enumerate(xml.findall(".//part")):
            result.append(value.attrib["name"])
        return result

    @staticmethod
    def getModel(file_content, selected_ic):
        xml = AutodeskEagle_SCH_Loader.getXML(file_content)
        nnc = NamedNetContainer()
        pa = PinAlias()

        query = ".//pinref[@part='{}']".format(selected_ic)
        query_parent = query + "/../.."
        for idx, parent in enumerate(xml.findall(query_parent)):
            node = parent.find(query)
            nnc.addEntry(
                pa.getIdForAlias(node.attrib["pin"]),
                STM32CubeMX_Loader.labelToNetName(parent.attrib["name"])
            )

        return nnc

    @staticmethod
    def getAllNetNames(file_content):
        xml = AutodeskEagle_SCH_Loader.getXML(file_content)
        result = []
        for idx, node in enumerate(xml.findall(".//net")):
            name = node.attrib["name"]
            if name not in result:
                result.append(name)
        return result

    @staticmethod
    def applyOperation(schematic, board, ic_name, targetContainer):
        oc = OperationContext()

        schematic_xml = ET.fromstring(schematic)
        board_xml = ET.fromstring(board)

        # add warnings for all ignored nets cause there pin's aren't connected        
        openContainer_it = filter(lambda entry: entry.net == "" and entry.new_net != "", targetContainer)
        for entry in openContainer_it:
            oc.warnings.append("Can't assign pin {} to net {} cause it is not connected.".format(entry.name, entry.new_net))

        goodContainer = TargetNetContainer.filterGood(targetContainer)

        # step 1: find name conflits in net names
        old_nets = [entry.net for entry in goodContainer]
        all_nets = AutodeskEagle_SCH_Loader.getAllNetNames(schematic_xml)
        unused_nets = filter(lambda name: name not in old_nets, all_nets)

        filteredContainer = TargetNetContainer()
        for entry in goodContainer:
            if entry.new_net in all_nets and entry.net in unused_nets:
                # the target name is used from an unused net, so it is ignored
                oc.errors.append("The net {} can't be renamed cause the new name {} is used somewhere else.".format(entry.net, entry.new_net))
            else:
                filteredContainer.append(entry)
        
        # step 2: decide temporary names for every net
        tmp_name_schema = "tmp_net_name_{}"
        i = 0
        tmp_name_reg = {}
        for entry in filteredContainer:
            tmp_name = tmp_name_schema.format(i)
            while tmp_name in all_nets:
                i += 1
                tmp_name = tmp_name_schema.format(i)
            tmp_name_reg[entry.name] = tmp_name
            i += 1

        # step 3: ...

        # step 4: profit!!!

        # step 5: rename all used nets to temp
        for entry in filteredContainer:
            for node in schematic_xml.findall(".//net[@name='{}']".format(entry.net)):
                node.set("name", tmp_name_reg[entry.name])
            for node in board_xml.findall(".//signal[@name='{}']".format(entry.net)):
                node.set("name", tmp_name_reg[entry.name])

        # step 6: rename all temp names to target names
        for entry in filteredContainer:
            for node in schematic_xml.findall(".//net[@name='{}']".format(tmp_name_reg[entry.name])):
                node.set("name", entry.new_net)
            for node in board_xml.findall(".//signal[@name='{}']".format(tmp_name_reg[entry.name])):
                node.set("name", entry.new_net)
            oc.log.append((entry.net, entry.new_net))

        oc.content = {
            "sch": ET.tostring(schematic_xml),
            "brd": ET.tostring(board_xml)
        }
        oc.successfull = True
        return oc