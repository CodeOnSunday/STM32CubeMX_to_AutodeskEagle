import os
import csv
import io
from .dataModel import NamedNetContainer, TargetNetContainer, OperationContext, Name
import xml.etree.cElementTree as ET

class Loader:
    @staticmethod
    def getModel(file_content):
        pass

    @staticmethod
    def applyOperation(file_content, target_container):
        pass

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
            return None
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

    @staticmethod
    def parseLine(line):
        if len(line) == 0 or line[0] == "#":
            return [], None
        parts = line.split("=")
        keys = parts[0].split(".")
        value = parts[1]
        return keys, value

    @staticmethod
    def getModel(file_content):
        nnc = NamedNetContainer()
        pa = PinAlias()

        for line in file_content.split("\n"):
            keys, value = STM32CubeMX_Loader.parseLine(line)
            if len(keys) == 2 and keys[1] == "GPIO_Label":
                nnc.addEntry(
                    Name(
                        keys[0],
                        pa.getIdForAlias(keys[0])
                    ),
                    Name(
                        value,
                        STM32CubeMX_Loader.labelToNetName(value)
                    )
                )

        return nnc

    @staticmethod
    def applyOperation(file_content, targetContainer):
        pa = PinAlias()
        oc = OperationContext()
        oc.content = []

        goodContainer = list(filter(lambda entry: entry.new_net is not None and entry.net != entry.new_net, targetContainer))

        def getEntryForSection(section):
            section_id = pa.getIdForAlias(section)
            for idx, entry in enumerate(goodContainer):
                if entry.name == section_id:
                    return entry, idx             
            return None, None

        def getLabelForEntry(entry):
            label = str(entry.new_net)
            if label[0] == "!":
                return "_" + label[1:]
            else:
                return label

        def addEntry(section):
            e, idx = getEntryForSection(section)
            if e is not None:
                del goodContainer[idx]
                label = getLabelForEntry(e)
                if label[0].isdigit():
                    oc.warnings.append("Can't assign label {} to {} cause it starts with a digit.".format(label, section))
                    return False

                oc.content.append("{}.GPIO_Label={}".format(current_section, label))
                oc.log.append(e)
                return True
            return False

        current_section = None
        section_used = False
        for line in file_content.split("\n"):
            keys, value = STM32CubeMX_Loader.parseLine(line)

            if len(keys) >= 1:
                ignore_line = False
                # if this section is new ...
                if current_section != keys[0]:
                    # ... and the section before is valid but without a label
                    if current_section is not None and section_used == False:
                        addEntry(current_section)

                    # save the new section
                    section_used = False
                    current_section = keys[0]

                if len(keys) == 2 and keys[1] == "GPIO_Label":
                    if addEntry(current_section):
                        ignore_line = True
                    section_used = True

                if ignore_line == False:
                    oc.content.append(line)
            else:
                oc.content.append(line)

        for entry in goodContainer:
            oc.errors.append("Can't assign label {} to {} cause the target pin is not configured.".format(entry.new_net, entry.name))

        oc.content = "\n".join(oc.content)
        oc.successfull = True
        return oc

class STM32CubeMX_CSV_Loader:
    @staticmethod
    def getModel(file_content):
        reader = csv.DictReader(io.StringIO(file_content), delimiter=",", quotechar='"')
        nnc = NamedNetContainer()
        pa = PinAlias()
        for line in reader:
            name = line["Name"]
            label = line["Label"]
            
            name = Name(
                name,
                pa.getIdForAlias(name)
            )
            if len(label) > 0:
                label = Name(
                    label,
                    STM32CubeMX_Loader.labelToNetName(label)
                )
            else:
                label = None

            nnc.addEntry(name, label)
        return nnc

    @staticmethod
    def applyOperation(file_content, targetContainer):
        write_buffer = io.StringIO()
        reader = csv.DictReader(io.StringIO(file_content), delimiter=",", quotechar='"')
        writer = csv.DictWriter(write_buffer, reader.fieldnames, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL, lineterminator="\r")
        pa = PinAlias()
        oc = OperationContext()

        writer.writeheader()

        for line in reader:
            line_id = pa.getIdForAlias(line["Name"])
            for entry in targetContainer:
                if entry.new_net is not None and line_id == entry.name:
                    line["Label"] = entry.new_net.escaped_name
                    oc.log.append(entry)

            if len(line["Label"]) > 0 and line["Label"][0] == "!":
                line["Label"] = "_" + line["Label"][1:]
            writer.writerow(line)

        oc.content = write_buffer.getvalue()
        oc.successfull = True
        write_buffer.close()
        return oc

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
                Name(
                    node.attrib["pin"],
                    pa.getIdForAlias(node.attrib["pin"])
                ),
                Name(
                    parent.attrib["name"],
                    STM32CubeMX_Loader.labelToNetName(parent.attrib["name"])
                )
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
        openContainer_it = filter(lambda entry: entry.net is None and entry.new_net is not None, targetContainer)
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
            tmp_name_reg[str(entry.name)] = tmp_name
            i += 1

        # step 3: ...

        # step 4: profit!!!

        # step 5: rename all used nets to temp
        for entry in filteredContainer:
            for node in schematic_xml.findall(".//net[@name='{}']".format(entry.net.real_name)):
                node.set("name", tmp_name_reg[str(entry.name)])
            for node in board_xml.findall(".//signal[@name='{}']".format(entry.net.real_name)):
                node.set("name", tmp_name_reg[str(entry.name)])

        # step 6: rename all temp names to target names
        for entry in filteredContainer:
            for node in schematic_xml.findall(".//net[@name='{}']".format(tmp_name_reg[str(entry.name)])):
                node.set("name", str(entry.new_net))
            for node in board_xml.findall(".//signal[@name='{}']".format(tmp_name_reg[str(entry.name)])):
                node.set("name", str(entry.new_net))
            oc.log.append(entry)

        oc.content = {
            "sch": ET.tostring(schematic_xml, encoding="unicode"),
            "brd": ET.tostring(board_xml, encoding="unicode")
        }
        oc.successfull = True
        return oc