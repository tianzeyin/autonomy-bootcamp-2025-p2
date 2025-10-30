"""
Heartbeat sending logic.
"""

from pymavlink import mavutil


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class HeartbeatSender:
    """
    HeartbeatSender class to send a heartbeat
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,  # Put your own arguments here
    ) -> "tuple[True, HeartbeatSender] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a HeartbeatSender object.
        """
        try:
            heartbeat_sender = cls(cls.__private_key, connection)
            return True, heartbeat_sender
        except (OSError, mavutil.mavlink.MAVError) as exception:
            print(
                f"Heartbeat receiver object creation failed: {exception}"
            )  # Using print since logger was not imported
            return False, None  # Create a Heartbeat Sender object

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,  # Put your own arguments here
    ) -> None:
        assert key is HeartbeatSender.__private_key, "Use create() method"

        # Do any intializiation here
        self.connection = connection

    def run(
        self,  # Put your own arguments here
    ) -> None:
        """
        Attempt to send a heartbeat message.
        """
        self.connection.mav.heartbeat_send(
            mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0
        )  # Send a heartbeat message


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
