import pytest

from network_data_template_app.message_bus_consumer import (
    MessageBusConsumer,
    fdn_to_pm_counter_status,
    _get_message_bus_connection_details,
)


@pytest.mark.asyncio
async def test_consume_messages_consumes_valid_messages(
    authentication_and_authorization,
    data_management_url,
    data_management_with_data_jobs,
    get_schema_valid_schema,
    message_bus_consumer_consumes_valid_messages,
):
    """Test that `consume_messages()` consumes valid messages."""
    await message_bus_consumer_consumes_valid_messages._consume_messages()
    assert (
        message_bus_consumer_consumes_valid_messages.total_messages_processed_count == 1
    )
    key = "urn:3gpp:dn:SubNetwork=Europe,SubNetwork=Ireland,MeContext=NR01gNodeBRadio00087,ManagedElement=NR01gNodeBRadio00087,GNBDUFunction=1,NRCellDU=NR01gNodeBRadio00087-1"
    assert key in fdn_to_pm_counter_status
    assert fdn_to_pm_counter_status[key] is True


@pytest.mark.asyncio
async def test_consume_messages_raises_system_exit_when_consuming_fatal_message(
    mock_apis, message_bus_consumer_consumes_err_messages
):
    """Test that `consume_messages()` will close the application when consuming a message with a fatal error."""
    with pytest.raises(SystemExit) as exc_info:
        await message_bus_consumer_consumes_err_messages._consume_messages()
        await message_bus_consumer_consumes_err_messages._consume_messages()

    assert exc_info.value.code == 1


@pytest.mark.asyncio
async def test_consume_messages_raises_system_exit_when_interacting_with_kafka(
    mock_apis, message_bus_consumer_with_kafka_exception
):
    """Test that `consume_messages()` will close the application when encountering an exception during any consumer operation."""
    with pytest.raises(SystemExit) as exc_info:
        await message_bus_consumer_with_kafka_exception._consume_messages()
        await message_bus_consumer_with_kafka_exception._consume_messages()

    assert exc_info.value.code == 1


def test_get_token_returns_valid_token(
    mock_apis, message_bus_consumer_consumes_valid_messages
):
    """Test that `get_token()` returns a valid token."""
    access_token = message_bus_consumer_consumes_valid_messages._get_token_consumer_client_callback(
        "oauth_cb"
    )
    assert access_token[0] == "2YotnFZFEjr1zCsicMWpAA"


def test_get_message_bus_conn_details_returns_valid_response(
    mock_apis, sync_oauth_client, message_bus_consumer_consumes_valid_messages
):
    """Test that `get_message_bus_conn_details()` returns valid message bus connection details."""
    message_bus_conn_details = _get_message_bus_connection_details(sync_oauth_client)
    assert (message_bus_conn_details["topic"]) == "ctr-processed"
    assert (message_bus_conn_details["hostname"]) == "bootstrap.example.com"
    assert (message_bus_conn_details["port"]) == 443


def test_get_message_bus_conn_details_raises_exception(
    data_management_api_no_data_jobs,
    sync_oauth_client,
    async_oauth_client,
    kafka_consumer_with_valid_messages,
):
    """Test that the application raises SystemExit when the kafka consumer configuration is invalid."""
    with pytest.raises(SystemExit) as exc_info:
        consumer = MessageBusConsumer(
            sync_oauth_client, async_oauth_client, kafka_consumer_with_valid_messages
        )
        consumer._initialize_consumer()

    assert exc_info.value.code == 1
