import os

class NamedNetEntry:
    def __init__(self, name, net):
        self.name = name
        self.net = net

    def __str__(self):
        return "{}: {}".format(self.name, self.net)

class NamedNetContainer(list):
    def addEntry(self, name, net):
        self.append(NamedNetEntry(name, net))

    def __str__(self):
        return os.linesep.join((str(e) for e in self))

    @staticmethod
    def filterGood(source):
        return NamedNetContainer( filter(lambda e: e.net != "", source))

    @staticmethod
    def filterMissingNet(source):
        return NamedNetContainer( filter(lambda e: e.net == "", source))

    def getEntryByName(self, name):
        for entry in self:
            if entry.name == name:
                return entry
        return None

class RenamedNetEntry(NamedNetEntry):
    def __init__(self, name, net, new_net):
        super().__init__(name, net)
        self.new_net = new_net

    def __str__(self):
        return "{}: {} => {}".format(self.name, self.net, self.new_net)

class TargetNetContainer(NamedNetContainer):
    @staticmethod
    def fromNNC(from_nets, to_nets):
        tnc = TargetNetContainer()
        for entry in from_nets:
            tnc.addEntry(entry.name, entry.net, "")
        for entry in to_nets:
            base = tnc.getEntryByName(entry.name)
            if base is not None:
                base.new_net = entry.net
            else:
                tnc.addEntry(entry.name, "", entry.net)
        return tnc

    @staticmethod
    def filterGood(source):
        return TargetNetContainer( filter(lambda e: e.net != "" and e.new_net != "" and e.net != e.new_net, source))

    def addEntry(self, name, net, new_net):
        self.append(RenamedNetEntry(name, net, new_net))

class OperationContext:
    def __init__(self):
        self.log = []
        self.errors = []
        self.warnings = []
        self.content = None
        self.successfull = False