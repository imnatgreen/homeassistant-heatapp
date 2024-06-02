"""Provides communication with a heatapp hub and its radiators."""

import datetime
import socket
import threading


class HeatappHub:
    """Communicate with a heatapp hub over UDP."""

    def __init__(self, host, port) -> None:
        """Initialise the client."""
        self._host = host
        self._port = port

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(20)
        self._sock = sock
        self._lock = threading.Lock()

        fw = self.get_fw()
        if fw is None:
            raise ConnectionError("Could not connect to the hub.")
        self.firmware = fw["firmware"]
        self.device_id = fw["device_id"]
        self.idu = fw["idu"]

        self.radiator_ids: list[int] = self.__get_radiator_ids()
        self.radiators_per_zone: list[int] = self.__get_radiators_per_zone()

    def send_command(self, command: str) -> str:
        """Send a command to the heatapp hub over UDP, and return the response. Ensures only one command is sent at a time."""
        with self._lock:
            try:
                self._sock.sendto(command.encode(), (self._host, self._port))
                data, _ = self._sock.recvfrom(1024)
                return data.decode().rstrip("\x00").rstrip("\x19")
            except socket.timeout:
                return "TIMEOUT"

    def __get_radiator_ids(self):
        """Get a list of available radiator ids."""
        command = "OPS2/"
        response = self.send_command(command).split(",")
        if response[0] == "OPOK":
            return [int(x) for x in response[2:]]
        else:
            return []

    def __get_radiators_per_zone(self):
        """Get a list of the number of physical radiators per zone."""
        command = "OPS3/"
        response = self.send_command(command).split(",")
        if response[0] == "OPOK":
            return [int(x) for x in response[2:]]
        else:
            return []

    def ready(self):
        """Check if the hub is ready to receive connections."""
        command = "OPS1/"
        response = self.send_command(command).split(",")
        if response[0] == "OPOK":
            return True
        else:
            return False

    def get_fw(self):
        """Get firmware details for the hub."""
        command = "OPF/"
        r = self.send_command(command).split(",")
        if r[0] == "OPOK":
            return {
                "firmware": r[1],
                "device_id": f"{r[2]}/{r[3]}",
                "idu": r[3],
            }

    def get_nw(self):
        """Get network details for the hub."""
        command = "OPS38/"
        r = self.send_command(command).split(",")
        if r[0] == "OPOK":
            return {
                "ip": f"{r[2]}.{r[3]}.{r[4]}.{r[5]}",
                "gateway": f"{r[6]}.{r[7]}.{r[8]}.{r[9]}",
                "subnet": f"{r[10]}.{r[11]}.{r[12]}.{r[13]}",
            }

    def get_time(self):
        """Get the current time reported by the hub."""
        command = "OPH/"
        r = self.send_command(command).split(",")
        if r[0] == "OPOK":
            d = [int(x) for x in r[1:]]
            return datetime.datetime(2000 + d[6], d[5], d[4], d[0], d[1], d[2])


class HeatappRadiator:
    """Provide a radiator to the hub."""

    def __init__(self, hub: HeatappHub, rad_id: int) -> None:
        """Initialise the radiator."""
        self.rad_id = rad_id
        self._hub = hub

        fw = self.__get_fw()
        self.firmware = fw["firmware"]
        self.serial = fw["serial"]

        self.power = self.__get_power()

    def get_temperature(self):
        """Get the current and target temperature from the radiator."""
        command = f"R#{self.rad_id}#1#0#0*?T/"
        r = self._hub.send_command(command).split(",")
        if r[0] == "OK":
            return {"current": int(r[1]), "target": int(r[2])}

    def set_temperature(self, target):
        """Set a new target temperature for the radiator."""
        rad_count = self._hub.radiators_per_zone[
            self._hub.radiator_ids.index(self.rad_id)
        ]
        okay = False

        for i in range(1, rad_count + 1):
            command = f"D#{self.rad_id}#{i}#0#0*T{target}/"
            r = self._hub.send_command(command).split(",")
            if r[0] == "OK":
                okay = True
            else:
                okay = False

        return okay

    def get_energy_usage(self):
        """Get today's energy usage for the radiator."""
        rad_count = self._hub.radiators_per_zone[
            self._hub.radiator_ids.index(self.rad_id)
        ]

        total = 0.0
        okay = False

        for i in range(1, rad_count + 1):
            command = f"R#{self.rad_id}#{i}#0#0*?UD/"
            r = self._hub.send_command(command).split(",")
            if r[0] == "OK":
                okay = True
                multiplier = int(r[1]) / 10000
                total += float(int(r[2]) * multiplier)
            else:
                okay = False

        if okay:
            return total
        return None

    def __get_power(self):
        """Get the total power of the radiators in the zone, in watts."""
        rad_count = self._hub.radiators_per_zone[
            self._hub.radiator_ids.index(self.rad_id)
        ]

        total = 0

        for i in range(1, rad_count + 1):
            command = f"R#{self.rad_id}#{i}#0#0*?UD/"
            r = self._hub.send_command(command).split(",")
            if r[0] == "OK":
                total += int(r[1])

        return total

    def __get_fw(self):
        """Get firmware details for the radiator (first radiator in each zone)."""
        command = f"R#{self.rad_id}#1#0#0*?F/"
        r = self._hub.send_command(command).split(",")
        if r[0] == "OK":
            return {
                "firmware": r[1],
                "serial": r[2],
            }
        return {
            "firmware": None,
            "serial": None,
        }
