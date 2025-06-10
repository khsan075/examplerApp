import pytest
import network_data_template_app.data_management as data_management


def test_get_data_jobs(mock_apis, sync_oauth_client, data_management_url):
    """
    Scenario: Get data jobs under our consumer ID.
    Expected Outcome: We should have a list of data jobs.
    Assertion: Test data contains 2 data jobs, so we should read 2.
    """
    data_jobs = data_management._get_data_jobs(sync_oauth_client)
    assert len(data_jobs) == 2


def test_no_data_jobs_raises_data_management_error(
    data_management_api_no_data_jobs, config, sync_oauth_client, data_management_url
):
    """
    Scenario: Get data jobs under our consumer ID.
    Expected Outcome: Receive zero data jobs.
    Assertion: DataManagementError is raised when 0 data jobs are received.
    """
    with pytest.raises(data_management.DataManagementError):
        data_management._get_data_jobs(sync_oauth_client)


def test_message_bus_connection_parsed(data_management_data_job):
    """
    Scenario: Received a data job.
    Expected Outcome: Data job is parsed to be used for a connection.
    Assertion: Parsed data job is a dict with keys `tuple`, `hostname`, `port`
    """
    message_bus_connection_details = data_management._parse_message_bus_connection(
        data_management_data_job
    )
    assert (
        message_bus_connection_details[0] == "test-topic"
        and message_bus_connection_details[1] == "https://example.org"
        and message_bus_connection_details[2] == "80"
    )
