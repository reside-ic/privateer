import json
import os.path


class PrivateerHost:
    def __init__(self, dat):
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


class PrivateerTarget:
    def __init__(self, dat):
        if dat["type"] != "volume":
            msg = "Only 'volume' targets are supported."
            raise Exception(msg)
        self.name = dat["name"]
        self.type = dat["type"]
        self.schedules = [BackupSchedule(s) for s in dat["schedules"]]
        if len(set([s.name for s in self.schedules])) < len(self.schedules):
            raise Exception(f"Schedules must have unique names. Found duplicate schedule names for target {self.name}")


class BackupSchedule:
    def __init__(self, dat):
        if dat["cron"] == "daily":
            self.schedule = "0 2 * * *"
            self.name = "daily"
        elif dat["cron"] == "weekly":
            self.schedule = "0 3 * * 1"
            self.name = "weekly"
        elif dat["cron"] == "monthly":
            self.schedule = "0 4 1 * *"
            self.name = "monthly"
        else:
            self.schedule = dat["cron"]
            self.name = "custom"
        if "retention_days" in dat:
            self.retention_days = dat["retention_days"]
        else:
            self.retention_days = None


class PrivateerConfig:
    def __init__(self, path):
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
