# *******************************************************************************
# Copyright (c) 2025 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

import logging
import os
import time

import pytest

from score.itf.plugins.dlt.dlt_receive import DltReceive, Protocol

logger = logging.getLogger(__name__)


# Datarouter messages with Context ID "STAT" sent every ~5s hence 10s to reliably capture and verify
CAPTURE_DURATION_SECONDS = 10

# DLT message identifiers for datarouter statistics
APP_ID = "DR"
CTX_ID = "STAT"

_QNX_DATAROUTER_CHECK_CMD = "/proc/boot/pidin | /proc/boot/grep datarouter"
_LINUX_DATAROUTER_CHECK_CMD = "ps -ef | grep datarouter | grep -v grep"

# pathspace ability provides the datarouter access to the `procnto` pathname prefix space
# required for mw/com message passing with mw::log frontend
_QNX_DATAROUTER_START_CMD = (
    "cd /usr/bin && nohup on -A nonroot,allow,pathspace -u 1051:1091 "
    "./datarouter --no_adaptive_runtime > /dev/null 2>&1 &"
)
_LINUX_DATAROUTER_START_CMD = (
    "cd /usr/bin && nohup ./datarouter --no_adaptive_runtime > /dev/null 2>&1 &"
)
# Multicast route directs all multicast traffic (224.0.0.0/4) out the container's
# network interface so DLT messages reach the host via the Docker bridge.
_LINUX_MULTICAST_ROUTE_CMD = (
    "ip route add 224.0.0.0/4 dev eth0 2>/dev/null || true"
)
_DATAROUTER_STARTUP_TIMEOUT_SEC = 2


def _is_qnx(target):
    """Detect if the target is running QNX."""
    _, out = target.execute("uname -s")
    return b"QNX" in out


@pytest.fixture
def datarouter_running(target):
    is_qnx = _is_qnx(target)

    if is_qnx:
        check_cmd = _QNX_DATAROUTER_CHECK_CMD
        start_cmd = _QNX_DATAROUTER_START_CMD
    else:
        check_cmd = _LINUX_DATAROUTER_CHECK_CMD
        start_cmd = _LINUX_DATAROUTER_START_CMD
        # Ensure multicast route exists for DLT message delivery
        target.execute(_LINUX_MULTICAST_ROUTE_CMD)

    exit_code, out = target.execute(check_cmd)
    output = out.decode(errors="replace")

    if "datarouter" not in output:
        # Verify the binary exists before attempting to start
        exit_code, _ = target.execute("test -x /usr/bin/datarouter")
        if exit_code != 0:
            pytest.fail("Datarouter binary not found at /usr/bin/datarouter on target")

        logger.info("Datarouter not running. Starting Datarouter..")
        exit_code, out = target.execute(start_cmd)
        logger.info("Start command exit_code=%s", exit_code)
        time.sleep(_DATAROUTER_STARTUP_TIMEOUT_SEC)

        _, out = target.execute(check_cmd)
        if "datarouter" not in out.decode(errors="replace"):
            pytest.fail("Failed to start datarouter on target")
        logger.info("Datarouter started successfully..")
    else:
        logger.info("Datarouter already running!")
    yield


def test_datarouter_remote_logging(datarouter_running, dlt_config):
    """Verifies remote logging of Dataraouter

    Starts Datarouter on the target if not already running, then
    the dlt_receive captures DLT messages on the test host
    on the multicast group for a fixed duration and checks for
    expected 'STAT' log messages in the captured DTL logs.
    """
    dlt_file = "/tmp/test_dlt_capture.dlt"

    # TODO: Replace with with DltWindow when fixed in ITF.
    with DltReceive(
        host_ip=dlt_config.host_ip,
        protocol=Protocol.UDP,
        file_name=dlt_file,
        binary_path=dlt_config.dlt_receive_path,
        multicast_ips=dlt_config.multicast_ips,
    ):
        time.sleep(CAPTURE_DURATION_SECONDS)

    assert os.path.exists(dlt_file), f"DLT file not created: {dlt_file}"

    with open(dlt_file, "rb") as f:
        dlt_data = f.read()

    logger.debug("DLT file size: %d bytes", len(dlt_data))

    # DLT extended header: APP-ID (4 bytes) followed by CTX-ID (4 bytes)
    pattern = f"{APP_ID}\x00\x00{CTX_ID}".encode()
    message_count = dlt_data.count(pattern)

    logger.info("Found %d messages with app_id=%s, context_id=%s", message_count, APP_ID, CTX_ID)

    assert message_count > 1, f"Expected atleast one DLT message, but got {message_count}"
