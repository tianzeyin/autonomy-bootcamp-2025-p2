"""
Bootcamp F2025

Main process to setup and manage all the other working processes
"""

import multiprocessing as mp
import queue
import time

from pymavlink import mavutil

from modules.common.modules.logger import logger
from modules.common.modules.logger import logger_main_setup
from modules.common.modules.read_yaml import read_yaml
from modules.command import command
from modules.command import command_worker
from modules.heartbeat import heartbeat_receiver_worker
from modules.heartbeat import heartbeat_sender_worker
from modules.telemetry import telemetry_worker
from utilities.workers import queue_proxy_wrapper
from utilities.workers import worker_controller
from utilities.workers import worker_manager


# MAVLink connection
CONNECTION_STRING = "tcp:localhost:12345"

# =================================================================================================
#                            ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
# =================================================================================================
# Set queue max sizes (<= 0 for infinity)
MAX_QUEUE = 5

# Set worker counts
HEARTBEAT_SENDER_COUNT = 1
HEARTBEAT_RECEIVER_COUNT = 1
TELEMETRY_COUNT = 1
COMMAND_COUNT = 1

# Any other constants
HEARTBEAT_INTERVAL = 1  # Seconds between heartbeat

# =================================================================================================
#                            ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
# =================================================================================================


def main() -> int:
    """
    Main function.
    """
    # Configuration settings
    result, config = read_yaml.open_config(logger.CONFIG_FILE_PATH)
    if not result:
        print("ERROR: Failed to load configuration file")
        return -1

    # Get Pylance to stop complaining
    assert config is not None

    # Setup main logger
    result, main_logger, _ = logger_main_setup.setup_main_logger(config)
    if not result:
        print("ERROR: Failed to create main logger")
        return -1

    # Get Pylance to stop complaining
    assert main_logger is not None

    # Create a connection to the drone. Assume that this is safe to pass around to all processes
    # In reality, this will not work, but to simplify the bootamp, preetend it is allowed
    # To test, you will run each of your workers individually to see if they work
    # (test "drones" are provided for you test your workers)
    # NOTE: If you want to have type annotations for the connection, it is of type mavutil.mavfile
    connection = mavutil.mavlink_connection(CONNECTION_STRING)
    connection.wait_heartbeat(timeout=30)  # Wait for the "drone" to connect

    # =============================================================================================
    #                          ↓ BOOTCAMPERS MODIFY BELOW THIS COMMENT ↓
    # =============================================================================================
    # Create a worker controller
    controller = worker_controller.WorkerController()

    # Create a multiprocess manager for synchronized queues
    mp_manager = mp.Manager()

    # Create queues
    heartbeat_queue = queue_proxy_wrapper.QueueProxyWrapper(mp_manager, MAX_QUEUE)
    telemetry_queue = queue_proxy_wrapper.QueueProxyWrapper(mp_manager, MAX_QUEUE)
    command_output_queue = queue_proxy_wrapper.QueueProxyWrapper(mp_manager, MAX_QUEUE)

    # Create worker properties for each worker type (what inputs it takes, how many workers)
    # Heartbeat sender
    result, heartbeat_sender_properties = worker_manager.WorkerProperties.create(
        count=HEARTBEAT_SENDER_COUNT,
        target=heartbeat_sender_worker.heartbeat_sender_worker,
        work_arguments=(connection, HEARTBEAT_INTERVAL, {}),
        # Heartbeats are emitted each second
        input_queues=[],
        output_queues=[],
        controller=controller,
        local_logger=main_logger,
    )
    if not result:
        main_logger.critical("Unable to send heartbeat sender properties")
        return -1

    # Get pylance to stop complaining
    assert heartbeat_sender_properties is not None

    # Heartbeat receiver
    result, heartbeat_receiver_properties = worker_manager.WorkerProperties.create(
        count=HEARTBEAT_RECEIVER_COUNT,
        target=heartbeat_receiver_worker.heartbeat_receiver_worker,
        work_arguments=(connection, HEARTBEAT_INTERVAL, {}),
        input_queues=[],
        output_queues=[heartbeat_queue],
        controller=controller,
        local_logger=main_logger,
    )
    if not result:
        main_logger.critical("Unable to send heartbeat receiver properties")
        return -1

    # Get pylance to stop complaining
    assert heartbeat_receiver_properties is not None

    # Telemetry
    result, telemetry_properties = worker_manager.WorkerProperties.create(
        count=TELEMETRY_COUNT,
        target=telemetry_worker.telemetry_worker,
        work_arguments=(connection, {}),
        input_queues=[],
        output_queues=[command_output_queue],
        controller=controller,
        local_logger=main_logger,
    )
    if not result:
        main_logger.critical("Unable to send telemetry properties")
        return -1

    # Get pylance to stop complaining
    assert telemetry_properties is not None

    # Command
    target_coordinates = command.Position(0, 0, 0)
    result, command_properties = worker_manager.WorkerProperties.create(
        count=COMMAND_COUNT,
        target=command_worker.command_worker,
        work_arguments=(connection, target_coordinates, {}),
        input_queues=[telemetry_queue],
        output_queues=[command_output_queue],
        controller=controller,
        local_logger=main_logger,
    )
    if not result:
        main_logger.critical("Unable to send command properties")
        return -1

    # Get pylance to stop complaining
    assert command_properties is not None

    # Create the workers (processes) and obtain their managers
    worker_managers: list[worker_manager.WorkerManager] = []

    result, heartbeat_sender_manager = worker_manager.WorkerManager.create(
        worker_properties=heartbeat_sender_properties,
        local_logger=main_logger,
    )
    if not result:
        main_logger.critical("Creation of Heartbeat Sender Manager Failed")
        return -1
    # GET PYLANCE TO STOP COMPLAINING
    assert heartbeat_sender_manager is not None
    worker_managers.append(heartbeat_sender_manager)

    result, heartbeat_receiver_manager = worker_manager.WorkerManager.create(
        worker_properties=heartbeat_receiver_properties,
        local_logger=main_logger,
    )
    if not result:
        main_logger.critical("Creation of Heartbeat Receiver Manager Failed")
        return -1
    # GET PYLANCE TO STOP COMPLAINING
    assert heartbeat_receiver_manager is not None
    worker_managers.append(heartbeat_receiver_manager)

    result, telemetry_manager = worker_manager.WorkerManager.create(
        worker_properties=telemetry_properties,
        local_logger=main_logger,
    )
    if not result:
        main_logger.critical("Creation of Telemetry Manager Failed")
        return -1
    # GET PYLANCE TO STOP COMPLAINING
    assert telemetry_manager is not None
    worker_managers.append(telemetry_manager)

    result, command_manager = worker_manager.WorkerManager.create(
        worker_properties=command_properties,
        local_logger=main_logger,
    )
    if not result:
        main_logger.critical("Creation of Command Manager Failed")
        return -1
    # GET PYLANCE TO STOP COMPLAINING
    assert command_manager is not None
    worker_managers.append(command_manager)

    # Start worker processes
    for manager in worker_managers:
        manager.start_workers()

    main_logger.info("Started")

    # Main's work: read from all queues that output to main, and log any commands that we make
    start_time = time.time()
    # Continue running for 100 seconds or until the drone disconnects
    total_queue = [heartbeat_queue, telemetry_queue, command_output_queue]
    while time.time() - start_time < 100:
        reading = total_queue.queue.get()
        if not total_queue.queue.empty():
            main_logger.info(f"Active reading from queue: {reading}")
        if reading == "DISCONNECTED":
            main_logger.critical("Stopping. Drone disconnected.")
            break

    # Stop the processes
    controller.request_exit()

    main_logger.info("Requested exit")

    # Fill and drain queues from END TO START
    heartbeat_queue.fill_and_drain_queue()
    telemetry_queue.fill_and_drain_queue()
    command_output_queue.fill_and_drain_queue()

    main_logger.info("Queues cleared")

    # Clean up worker processes
    for manager in worker_managers:
        manager.join_workers()

    main_logger.info("Stopped")

    # We can reset controller in case we want to reuse it
    # Alternatively, create a new WorkerController instance
    controller.clear_exit()

    # =============================================================================================
    #                          ↑ BOOTCAMPERS MODIFY ABOVE THIS COMMENT ↑
    # =============================================================================================

    return 0


if __name__ == "__main__":
    result_main = main()
    if result_main < 0:
        print(f"Failed with return code {result_main}")
    else:
        print("Success!")
