import asyncio
import json

import pytest

from network_data_template_app.message_bus_consumer import fdn_to_pm_counter_status
from network_data_template_app.report_generator import ReportGenerator


async def block_until(condition):
    while not condition():
        await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_report_scheduler(
    network_configuration_api, no_log_certs, config, async_oauth_client, caplog
):
    """Test two intervals of the report scheduler. Each interval provides 10 results, so in the end expect 20."""
    with open(
        "tests/fdn_to_pm_counter_status_mock.json", "r", encoding="utf-8"
    ) as f_map:
        fdn_to_pm_counter_status.clear()
        fdn_to_pm_counter_status.update(json.load(f_map))

    report = ReportGenerator(async_oauth_client, clear_data_upon_usage=False)
    report.start_schedule(trigger="interval", seconds=0.2)

    fdn_prefix = "urn:3gpp:dn"  # ensure we have the full FDN by checking for the prefix

    await asyncio.wait_for(
        block_until(lambda: fdn_prefix in caplog.text), timeout=1
    )  # 1st interval
    assert caplog.text.count(fdn_prefix) == 10

    await asyncio.wait_for(
        block_until(lambda: caplog.text.count(fdn_prefix) == 20), timeout=1
    )  # 2nd interval
    assert caplog.text.count(fdn_prefix) == 20

    assert "8 out of 10" in caplog.text

    report.stop_schedule()
    fdn_to_pm_counter_status.clear()


@pytest.mark.asyncio
async def test_report_scheduler_no_counters(
    network_configuration_api, no_log_certs, config, async_oauth_client, caplog
):
    """Test the report scheduler with no PM counters collected. Expected log message includes 'No PM counters collected' and a table of NRCellDUs"""
    with open(
        "tests/fdn_to_pm_counter_status_false.json", "r", encoding="utf-8"
    ) as f_map:
        fdn_to_pm_counter_status.clear()
        fdn_to_pm_counter_status.update(json.load(f_map))

    report = ReportGenerator(async_oauth_client, clear_data_upon_usage=False)
    report.start_schedule(trigger="interval", seconds=0.2)

    fdn_prefix = "urn:3gpp:dn"  # ensure we have the full FDN by checking for the prefix

    await asyncio.wait_for(block_until(lambda: fdn_prefix in caplog.text), timeout=1)
    assert "0 out of 10" in caplog.text
    assert caplog.text.count(fdn_prefix) == 10

    report.stop_schedule()
    fdn_to_pm_counter_status.clear()


@pytest.mark.asyncio
async def test_report_scheduler_ncmp_error(
    mock_apis, no_log_certs, config, async_oauth_client, caplog
):
    """Test the report scheduler with no PM counters collected. Expected log message includes 'No PM counters collected' and a table of NRCellDUs"""
    with open(
        "tests/fdn_to_pm_counter_status_false.json", "r", encoding="utf-8"
    ) as f_map:
        fdn_to_pm_counter_status.clear()
        fdn_to_pm_counter_status.update(json.load(f_map))

    report = ReportGenerator(async_oauth_client, clear_data_upon_usage=False)
    report.start_schedule(trigger="interval", seconds=0.2)

    await asyncio.wait_for(block_until(lambda: "UNKNOWN" in caplog.text), timeout=1)
    assert "UNKNOWN" in caplog.text
    assert caplog.text.count("operationalState=UNKNOWN") == 10

    report.stop_schedule()
    fdn_to_pm_counter_status.clear()
