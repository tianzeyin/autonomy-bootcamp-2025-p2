"""
Heartbeat worker that sends heartbeats periodically.
"""

import os
import pathlib
import time

from pymavlink import mavutil

from utilities.workers import worker_controller
from . import heartbeat_sender
from ..common.modules.logger import logger


# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
def heartbeat_sender_worker(
    connection: mavutil.mavfile,
    controller: worker_controller.WorkerController,  # Place your own arguments here
    # Add other necessary worker arguments here
) -> None:
    """
    Worker process.

    args... describe what the arguments are
    connection is an active MAVLink pipeline to communicate with drone
    controller controls worker requests
    """
    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    # Instantiate logger
    worker_name = pathlib.Path(__file__).stem
    process_id = os.getpid()
    result, local_logger = logger.Logger.create(f"{worker_name}_{process_id}", True)
    if not result:
        print("ERROR: Worker failed to create logger")
        return

    # Get Pylance to stop complaining
    assert local_logger is not None

    local_logger.info("Logger initialized", True)

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Instantiate class object (heartbeat_sender.HeartbeatSender)
    result, heartbeat_instance = heartbeat_sender.HeartbeatSender.create(connection)
    if not result:
        local_logger.error("Failed to create Heartbeat Sender object!")
        return

    # Main loop: do work.
    while not controller.is_exit_requested():
        controller.check_pause()
        heartbeat_instance.run()
        local_logger.info("Heartbeat Sent!")
        time.sleep(1)



# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================
