import json


class PorterHost:
    def __init__(self, dat):
        self.name = dat["name"]
        self.hostname = dat["hostname"]
        if "user" in dat:
            self.user = dat["user"]
        else:
            self.user = None
        if "port" in dat:
            self.port = dat["port"]
        else:
            self.port = None


class PorterTarget:
    def __init__(self, dat):
        if dat["type"] != "volume":
            msg = "Only 'volume' targets are supported."
            raise Exception(msg)
        self.name = dat["name"]
        self.type = dat["type"]


class PorterConfig:
    def __init__(self, path):
        with open(f"{path}/porter.json") as f:
            config = json.load(f)
        self.targets = [PorterTarget(t) for t in config["targets"]]
        self.hosts = [PorterHost(h) for h in config["hosts"]]

    def get_host(self, name):
        match = [h for h in self.hosts if h.name == name]
        if len(match) > 1:
            msg = f"Invalid arguments: two hosts with the name '{name}' found."
            raise Exception(msg)
        return match[0]
