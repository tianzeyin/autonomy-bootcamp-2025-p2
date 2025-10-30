"""
Heartbeat receiving logic.
"""

from pymavlink import mavutil

from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class HeartbeatReceiver:
    """
    HeartbeatReceiver class to send a heartbeat
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> "tuple[True, HeartbeatReceiver] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a HeartbeatReceiver object.
        """
        try:
            heartbeat_receiver = cls(cls.__private_key, connection, local_logger)
            return True, heartbeat_receiver
        except (OSError, mavutil.mavlink.MAVError) as exception:
            local_logger.error(f"Heartbeat Receiver object creation failed: {exception}")
            return False, None  #  Create a Heartbeat Receiver object

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        local_logger: logger.Logger,
    ) -> None:
        assert key is HeartbeatReceiver.__private_key, "Use create() method"

        # Do any intializiation here
        self.connection = connection
        self.local_logger = local_logger
        self.missed_count = 0
        self.state = "DISCONNECTED"

    def run(
        self,
    ) -> None:
        """
        Attempt to recieve a heartbeat message.
        If disconnected for over a threshold number of periods,
        the connection is considered disconnected.
        """
        try:
            signal = self.connection.recv_match(type="HEARTBEAT", blocking=False)
            if signal is not None:
                self.missed_count = 0
                if self.state != "CONNECTED":
                    self.state = "CONNECTED"
                    self.local_logger.info("Heartbeat Received!", True)
                self.local_logger.info("Heartbeat received", True)
            else:
                self.missed_count += 1
                if self.state != "DISCONNECTED" and self.missed_count >= 5:
                    self.state = "DISCONNECTED"
                    self.local_logger.info("Disconnected!", True)
            time.sleep(0.2)
        except (OSError, mavutil.mavlink.MAVError) as exception:
            self.local_logger.error(f"Heartbeat Receiver Error: {exception}", True)


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
