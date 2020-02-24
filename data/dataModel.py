import os

class Name:
    def __init__(self, real_name, escaped_name):
        self.real_name = real_name
        self.escaped_name = escaped_name

    def __str__(self):
        return self.escaped_name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.escaped_name == other
        elif isinstance(other, Name):
            return self.escaped_name == other.escaped_name
        elif other is None:
            return False
        else:
            raise NotImplementedError()

    def __ne__(self, other):
        return not self.__eq__(other)

class NamedNetEntry:
    def __init__(self, name, net):
        self.name = name
        self.net = net

    def __str__(self):
        return "{}: {}".format(str(self.name), str(self.net))

class NamedNetContainer(list):
    def addEntry(self, name, net):
        self.append(NamedNetEntry(name, net))

    def __str__(self):
        return os.linesep.join((str(e) for e in self))

    @staticmethod
    def filterGood(source):
        return NamedNetContainer( filter(lambda e: e.net is not None, source))

    @staticmethod
    def filterMissingNet(source):
        return NamedNetContainer( filter(lambda e: e.net is None, source))

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
        return "{}: {} => {}".format(str(self.name), str(self.net), str(self.new_net))

class TargetNetContainer(NamedNetContainer):
    @staticmethod
    def fromNNC(from_nets, to_nets):
        tnc = TargetNetContainer()
        for entry in from_nets:
            tnc.addEntry(entry.name, entry.net, None)
        for entry in to_nets:
            base = tnc.getEntryByName(entry.name)
            if base is not None:
                base.new_net = entry.net
            else:
                tnc.addEntry(entry.name, None, entry.net)
        return tnc

    @staticmethod
    def filterGood(source):
        return TargetNetContainer( filter(lambda e: e.net is not None and e.new_net is not None and e.net != e.new_net, source))

    def addEntry(self, name, net, new_net):
        self.append(RenamedNetEntry(name, net, new_net))

class OperationContext:
    def __init__(self):
        self.log = []
        self.errors = []
        self.warnings = []
        self.content = None
        self.successfull = False