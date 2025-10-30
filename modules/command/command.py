"""
Decision-making logic.
"""

import math

from pymavlink import mavutil

from ..common.modules.logger import logger
from ..telemetry import telemetry


class Position:
    """
    3D vector struct.
    """

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
class Command:  # pylint: disable=too-many-instance-attributes
    """
    Command class to make a decision based on recieved telemetry,
    and send out commands based upon the data.
    """

    __private_key = object()

    @classmethod
    def create(
        cls,
        connection: mavutil.mavfile,
        target: Position,  # Put your own arguments here
        local_logger: logger.Logger,
    ) -> "tuple[True, Command] | tuple[False, None]":
        """
        Falliable create (instantiation) method to create a Command object.
        """
        try:
            command = cls(cls.__private_key, connection, target, local_logger)
            return True, command
        except (OSError, mavutil.mavlink.MAVError) as exception:
            local_logger.error(f"Command object creation failed: {exception}")
            return False, None  #  Create a Command object

    def __init__(
        self,
        key: object,
        connection: mavutil.mavfile,
        target: Position,  # Put your own arguments here
        local_logger: logger.Logger,
    ) -> None:
        assert key is Command.__private_key, "Use create() method"

        # Do any intializiation here
        self.connection = connection
        self.target = target
        self.local_logger = local_logger
        self.xv = 0
        self.yv = 0
        self.zv = 0
        self.n_val = 0

    def run(
        self,
        target: Position,
        path: telemetry.TelemetryData,  # Put your own arguments here
    ) -> str:
        """
        Make a decision based on received telemetry data.
        """
        self.n_val += 1
        self.xv += path.x_velocity
        self.yv += path.y_velocity
        self.zv += path.z_velocity
        average_velocity = (
            self.xv / self.n_val,
            self.yv / self.n_val,
            self.zv / self.n_val,
        )
        # Log average velocity for this trip so far
        self.local_logger.info(f"Average Velocity: {average_velocity}")

        # Use COMMAND_LONG (76) message, assume the target_system=1 and target_componenet=0
        # The appropriate commands to use are instructed below

        # Adjust height using the comand MAV_CMD_CONDITION_CHANGE_ALT (113)
        # String to return to main: "CHANGE_ALTITUDE: {amount you changed it by, delta height in meters}"

        # Adjust direction (yaw) using MAV_CMD_CONDITION_YAW (115). Must use relative angle to current state
        # String to return to main: "CHANGING_YAW: {degree you changed it by in range [-180, 180]}"
        # Positive angle is counter-clockwise as in a right handed system
        if target.z - path.z > 0.5 or target.z - path.z < -0.5:
            amount_to_move = target.z - path.z
            # move the drone
            self.connection.mav.command_long_send(
                1,
                0,
                mavutil.mavlink.MAV_CMD_CONDITION_CHANGE_ALT,
                confirmation=0,
                param1=1,
                param2=0,
                param3=0,
                param4=0,
                param5=0,
                param6=0,
                param7=target.z,
            )
            return f"CHANGE_ALTITUDE: {amount_to_move}"

        target_angle = math.atan2(target.y - path.y, target.x - path.x)
        # Angle (radians) measured counter-clockwise of x
        angle_difference = target_angle - path.yaw
        # Distance needed for drone to face target
        if angle_difference > (math.pi):
            angle_difference = -1 * ((2 * math.pi) - angle_difference)
        elif angle_difference < -1 * (math.pi):
            angle_difference = -1 * ((-2 * math.pi) - angle_difference)
        # Determines the shortest value of angle_difference (<+180 or -180) instead of using values 180 to 360
        angle_difference_deg = math.degrees(angle_difference)
        if angle_difference_deg > 5 or angle_difference_deg < -5:
            # Drone must be corrected if >5deg from target
            direction = -1 if angle_difference_deg > 0 else 1
            self.connection.mav.command_long_send(
                1,
                0,
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                confirmation=0,
                param1=angle_difference_deg,
                param2=5,
                param3=direction,
                param4=1,
                param5=0,
                param6=0,
                param7=0,
            )
            return f"CHANGING_YAW: {angle_difference_deg}"
        return None


# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
