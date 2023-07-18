import json
import os.path


class Serializable(dict):
    def __init__(self):
        dict.__init__(self)

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


class PrivateerHost(Serializable):
    def __init__(self, dat):
        Serializable.__init__(self)
        host_type = dat["type"]
        if host_type != "remote" and host_type != "local":
            msg = "Host type must be 'remote' or 'local'."
            raise Exception(msg)
        self.name = dat["name"]
        self.host_type = host_type
        self.path = dat["path"]
        if host_type == "local" and not os.path.isabs(self.path):
            self.path = os.path.abspath(self.path)
            print(f"Relative path provided; resolving to {self.path}")
        if host_type == "remote":
            self.hostname = dat["hostname"]
            if "user" in dat:
                self.user = dat["user"]
            else:
                self.user = None
            if "port" in dat:
                self.port = dat["port"]
            else:
                self.port = None


class PrivateerTarget(Serializable):
    def __init__(self, dat):
        Serializable.__init__(self)
        if dat["type"] != "volume":
            msg = "Only 'volume' targets are supported."
            raise Exception(msg)
        self.name = dat["name"]
        self.type = dat["type"]
        if "schedules" in dat:
            self.schedules = [BackupSchedule(s) for s in dat["schedules"]]
            if len({s.name for s in self.schedules}) < len(self.schedules):
                ex = f"Schedules must have unique names. Found duplicate schedule names for target {self.name}"
                raise Exception(ex)
        else:
            self.schedules = []


class BackupSchedule(Serializable):
    def __init__(self, dat):
        Serializable.__init__(self)
        self.name = dat["name"]
        if dat["name"] == "daily":
            self.schedule = "0 2 * * *"
        elif dat["name"] == "weekly":
            self.schedule = "0 3 * * 1"
        elif dat["name"] == "monthly":
            self.schedule = "0 4 1 * *"
        else:
            self.schedule = dat["cron"]
        if "retention_days" in dat:
            self.retention_days = dat["retention_days"]
        else:
            self.retention_days = None


class PrivateerConfig(Serializable):
    def __init__(self, path):
        Serializable.__init__(self)
        with open(f"{path}/privateer.json") as f:
            config = json.load(f)
        self.targets = [PrivateerTarget(t) for t in config["targets"]]
        self.hosts = [PrivateerHost(h) for h in config["hosts"]]

    def get_host(self, name):
        match = [h for h in self.hosts if h.name == name]
        if len(match) > 1:
            msg = f"Invalid arguments: two hosts with the name '{name}' found."
            raise Exception(msg)
        if len(match) == 0:
            msg = f"Invalid arguments: no host with the name '{name}' found."
            raise Exception(msg)
        return match[0]
