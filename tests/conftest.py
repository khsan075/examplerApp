"""Configure a Flask fixture based off the Application defined in main.py"""

import asyncio
import json
import os
import pickle
import re
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urljoin

import httpx
import pytest
import pytest_asyncio
import respx
from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuth2Client
from confluent_kafka import KafkaError, KafkaException
from fastapi.testclient import TestClient
from httpx import Response

import network_data_template_app.data_management as data_management
from network_data_template_app.config import get_config
from network_data_template_app.message_bus_consumer import MessageBusConsumer
from network_data_template_app.metrics import metrics_registry
from network_data_template_app.mtls_logging import _MTLSLogger, _ConsoleLogger, Severity
from network_data_template_app.oauth import oauth, synchronous_oauth
from network_data_template_app.server import app as test_app


def pytest_generate_tests():
    populate_environment_variables()


def reset_counters():
    for counter in metrics_registry.counters.values():
        counter.reset()


@pytest.fixture(name="mock_apis")
def fixture_mock_apis(config):
    """Setup mock APIs"""
    with respx.mock(assert_all_called=False) as respx_mock:
        # Authentication & Authorization
        login_url = urljoin(
            config.get("iam_base_url"),
            "/auth/realms/master/protocol/openid-connect/token",
        )
        # The % operator is overloaded in `respx`. It's a quirky but valid way to attach a response to the mocked request.
        respx_mock.post(login_url) % Response(
            status_code=200,
            json={
                "access_token": "2YotnFZFEjr1zCsicMWpAA",
                "token_type": "Bearer",
                "expires_in": 3600,
                "example_parameter": "example_value",
            },
        )  # Example reply from OAuth2 spec: https://datatracker.ietf.org/doc/html/rfc6749#section-4.4.3

        # App Logging
        log_endpoint = f"https://{config.get('log_endpoint')}"
        respx_mock.post(log_endpoint)

        # Topology & Inventory
        topology_endpoint = urljoin(
            config.get("iam_base_url"), "/topology-inventory/v1alpha11"
        )
        topology_matcher = re.compile(f"{topology_endpoint}/")
        with open(
            "./tests/topology_response.json",
            "r",
            encoding="utf-8",
        ) as f:
            response_json = json.load(f)
        expected_headers = {"Authorization": "Bearer 2YotnFZFEjr1zCsicMWpAA"}

        respx_mock.get(
            f"{topology_endpoint}/domains/RAN/entities?targetFilter=/NRCellDU/sourceIds&limit=10",
            headers__contains=expected_headers,
        ) % Response(status_code=200, json=response_json)
        respx_mock.get(topology_matcher) % Response(status_code=403, text="Forbidden")

        # Data Management
        data_management_endpoint = (
            config.get("iam_base_url")
            + "/dmm-data-collection-controller/data-access/v2/"
            + config.get("iam_client_id")
            + "/dataJobs"
        )
        with open(
            "./tests/data_management_response.json",
            "r",
            encoding="utf-8",
        ) as f:
            respx_mock.get(data_management_endpoint) % Response(
                status_code=200, json=json.load(f)
            )

        yield respx_mock


@pytest.fixture
def data_management_api_no_data_jobs(mock_apis, config):
    data_management_endpoint = (
        config.get("iam_base_url")
        + "/dmm-data-collection-controller/data-access/v2/"
        + config.get("iam_client_id")
        + "/dataJobs"
    )
    mock_apis.get(data_management_endpoint) % Response(status_code=200, json=[])
    yield mock_apis


@pytest.fixture
def network_configuration_api(mock_apis, config):
    # Network Configuration
    # example URL: https://eic-host/ncmp/v1/ch/D9EC3ED18972159ACBF75A71BE3AB022/data/ds/ncmp-datastore:passthrough-operational?resourceIdentifier=/GNBDUFunction%5B%40id%3D1%5D/NRCellDU%5B%40id%3DNR01gNodeBRadio00006-1%5D
    network_configuration_pattern_odd = (
        config.get("iam_base_url")
        + r"\/ncmp\/v1\/ch\/.*\/data\/ds\/ncmp-datastore:.*\?resourceIdentifier=.*-[13579]%5D.*"
    )
    network_configuration_pattern_even = (
        config.get("iam_base_url")
        + r"\/ncmp\/v1\/ch\/.*\/data\/ds\/ncmp-datastore:.*\?resourceIdentifier=.*-[02468]%5D.*"
    )
    network_configuration_matcher_odd = re.compile(network_configuration_pattern_odd)
    network_configuration_matcher_even = re.compile(network_configuration_pattern_even)
    network_configuration_response_enabled = json.loads(
        '{"NRCellDU": [{"id": "NR01gNodeBRadio00042-0", "attributes": {"operationalState": "ENABLED"}}]}'
    )
    network_configuration_response_disabled = json.loads(
        '{"NRCellDU": [{"id": "NR01gNodeBRadio00042-1", "attributes": {"operationalState": "DISABLED"}}]}'
    )
    mock_apis.get(network_configuration_matcher_even) % Response(
        status_code=200, json=network_configuration_response_enabled
    )
    mock_apis.get(network_configuration_matcher_odd) % Response(
        status_code=200, json=network_configuration_response_disabled
    )
    yield mock_apis


@pytest.fixture
def authentication_and_authorization(config):
    with respx.mock(assert_all_called=False) as respx_mock:
        # Authentication & Authorization
        login_url = urljoin(
            config.get("iam_base_url"),
            "/auth/realms/master/protocol/openid-connect/token",
        )
        # The % operator is overloaded in `respx`. It's a quirky but valid way to attach a response to the mocked request.
        respx_mock.post(login_url) % Response(
            status_code=200,
            json={
                "access_token": "2YotnFZFEjr1zCsicMWpAA",
                "token_type": "Bearer",
                "expires_in": 3600,
                "example_parameter": "example_value",
            },
        )
        yield respx_mock


@pytest.fixture
def data_management_with_data_jobs(config):
    with respx.mock(assert_all_called=False) as respx_mock:
        data_management_endpoint = (
            config.get("iam_base_url")
            + "/dmm-data-collection-controller/data-access/v2/"
            + config.get("iam_client_id")
            + "/dataJobs"
        )
        with open(
            "./tests/data_management_response.json",
            "r",
            encoding="utf-8",
        ) as f:
            respx_mock.get(data_management_endpoint) % Response(
                status_code=200, json=json.load(f)
            )

        yield respx_mock


@pytest.fixture
def get_topology_get_nr_cell_dus_response():
    # Load the JSON response from an external file
    with open(
        "./tests/topology_get_nr_cell_dus_response.json", "r", encoding="utf-8"
    ) as f:
        topology_response = json.load(f)
        yield topology_response


@pytest.fixture
def get_schema_valid_schema(config):
    """
    Fixture to mock the schema registry API response using a JSON file.

    - Reads the schema response from `./tests/schema_registry_response.json`
    - Mocks a successful response with status code 200
    - Yields the mocked API instance for testing

    Args:
        mock_apis: A mock API fixture that intercepts HTTP requests.
        config: A configuration object containing API base URLs.

    Yields:
        A mocked API instance returning a predefined schema registry response.
    """

    with respx.mock(assert_all_called=False) as respx_mock:
        schema_registry_endpoint = (
            config.get("iam_base_url") + "/schema-registry-sr" + "/view/schemas/ids/125"
        )

        # Load the JSON response from an external file
        with open("./tests/schema_registry_response.json", "r", encoding="utf-8") as f:
            schema_response = json.load(f)

        respx_mock.get(schema_registry_endpoint) % Response(
            status_code=200, json=schema_response
        )

        # # Mock the API response using respx
        # mock_apis.get(schema_registry_endpoint) % Response(status_code=200, json=schema_response)

        yield respx_mock


@pytest.fixture
def data_management_data_job():
    yield {
        "streamingConfigurationKafka": {
            "topicName": "test-topic",
            "kafkaBootstrapServers": [
                {"hostname": "https://example.org", "portAddress": "80"}
            ],
        }
    }


@pytest.fixture(name="sync_oauth_client")
def sync_oauth_client():
    """Setup OAuth Session"""
    config = get_config()
    login_path = "/auth/realms/master/protocol/openid-connect/token"
    login_url = urljoin(config.get("iam_base_url"), login_path)
    sync_oauth_client = OAuth2Client(
        config.get("iam_client_id"),
        config.get("iam_client_secret"),
        scope="openid",
        token_endpoint=login_url,
        verify=False,
        leeway=250,
    )
    token = sync_oauth_client.fetch_token()
    yield sync_oauth_client
    sync_oauth_client.close()


@pytest_asyncio.fixture(name="async_oauth_client")
async def async_oauth_client():
    """Setup OAuth Session"""
    config = get_config()
    login_path = "/auth/realms/master/protocol/openid-connect/token"
    login_url = urljoin(config.get("iam_base_url"), login_path)
    async_oauth_client = AsyncOAuth2Client(
        config.get("iam_client_id"),
        config.get("iam_client_secret"),
        scope="openid",
        token_endpoint=login_url,
        verify=False,
        leeway=250,
    )
    token = await async_oauth_client.fetch_token()
    yield async_oauth_client
    await async_oauth_client.aclose()


@pytest.fixture(name="app")
def fixture_app(mock_apis, network_configuration_api):
    # pylint: disable=unused-argument

    # Why 'yield'? See: https://docs.pytest.org/en/7.1.x/how-to/fixtures.html#dynamic-scope
    yield
    reset_counters()


@pytest_asyncio.fixture(name="client")
async def client(app, async_oauth_client):
    """Every time a test wants a client, give it a new copy of our Application"""
    test_client = TestClient(test_app)
    await oauth.set_oauth_client(async_oauth_client)
    yield test_client


@pytest.fixture(name="sync_client")
def sync_client(app, sync_oauth_client):
    """Every time a test wants a client, give it a new copy of our Application"""
    test_client = TestClient(test_app)
    synchronous_oauth.set_oauth_client(sync_oauth_client)
    yield test_client


@pytest.fixture(name="config")
def fixture_config():
    """Every time a test wants a config, give it a stub"""
    return get_config()


@pytest.fixture(scope="function")
def no_log_certs():
    """
    Remove references to log certs to simulate them being undefined.
    This would simulate a user not setting these at instantiation time.
    """
    os.environ["APP_KEY"] = ""
    os.environ["APP_CERT"] = ""
    os.environ["APP_CERT_FILE_PATH"] = ""

    # Why 'yield'? See: https://docs.pytest.org/en/7.1.x/how-to/fixtures.html#dynamic-scope
    yield
    populate_environment_variables()


@pytest.fixture(scope="function")
def no_platform_access():
    """
    Remove references to iam base url to simulate lack of api access.
    This would simulate a user not setting these at instantiation time.
    """
    os.environ["IAM_BASE_URL"] = ""

    # Why 'yield'? See: https://docs.pytest.org/en/7.1.x/how-to/fixtures.html#dynamic-scope
    yield
    populate_environment_variables()


@pytest.fixture
def data_management_url(config):
    # Overwrite the data management URL with test config instead.
    data_management.DATA_MANAGEMENT_URL = f"{config.get('iam_base_url')}/dmm-data-collection-controller/data-access/v2/{config.get('iam_client_id')}/dataJobs"


@pytest.fixture
def kafka_consumer_with_valid_messages():
    """Kafka consumer that consumes valid messages."""
    consumer = MagicMock()

    # Create mock Kafka messages
    msg1 = MagicMock()
    msg1.value.return_value = b"Message 1"
    msg1.error.return_value = None

    msg2 = MagicMock()
    msg2.value.return_value = b"Message 2"
    msg2.error.return_value = None

    msg_error = MagicMock()
    msg_error.error.return_value = KafkaError(
        KafkaError._INVALID_ARG, "Invalid argument or configuration", fatal=False
    )  # Does not raise SystemExit

    msg3 = MagicMock()

    # Read mock header and value from a bin file
    with open("tests/pm_message_header.bin", "rb") as file:
        mock_header = pickle.load(file)

    with open("tests/pm_message_value.bin", "rb") as file:
        mock_value = pickle.load(file)

    msg3.headers.return_value = mock_header
    msg3.value.return_value = mock_value
    msg3.error.return_value = None

    msg4 = MagicMock()

    # Read mock header and value from a bin file
    with open("tests/pm_message_wrong_header.bin", "rb") as file:
        mock_header = pickle.load(file)

    with open("tests/pm_message_value.bin", "rb") as file:
        mock_value = pickle.load(file)

    msg4.headers.return_value = mock_header
    msg4.value.return_value = mock_value
    msg4.error.return_value = None

    # Simulate `consume()` returning different messages
    consumer.consume.return_value = [msg3, msg4, msg2, msg1, msg2, msg_error]

    yield consumer


@pytest.fixture
def kafka_consumer_with_err_messages():
    """Kafka consumer that consumes error messages."""
    consumer = MagicMock()

    msg1 = MagicMock()
    msg1.value.return_value = b"Message 1"
    msg1.error.return_value = None

    msg_error = MagicMock()
    msg_error.value.return_value = None
    msg_error.error.return_value = KafkaError(
        KafkaError._FATAL, "Broker connection failed.", fatal=True
    )

    closed = False

    def set_closed():
        nonlocal closed
        closed = True

    def consume_side_effect(*args, **kwargs):
        if closed:
            raise RuntimeError()
        return [msg1, msg_error]

    consumer.close.side_effect = set_closed
    consumer.consume.side_effect = consume_side_effect

    yield consumer


@pytest.fixture
def kafka_consumer_raises_kafka_exception():
    """Kafka consumer that raises KafkaException."""
    consumer = MagicMock()

    kafka_error = KafkaError(KafkaError._UNKNOWN_PARTITION, "Mock error", True)
    kafka_exception = KafkaException(kafka_error)

    closed = False

    def set_closed():
        nonlocal closed
        closed = True

    def consume_side_effect(*args, **kwargs):
        if closed:
            raise RuntimeError()
        else:
            raise kafka_exception

    consumer.close.side_effect = set_closed
    consumer.consume.side_effect = consume_side_effect

    yield consumer


@pytest_asyncio.fixture
async def message_bus_consumer_consumes_valid_messages(
    sync_oauth_client,
    async_oauth_client,
    kafka_consumer_with_valid_messages,
    data_management_url,
    get_topology_get_nr_cell_dus_response,
):
    """Async fixture for MessageBusConsumer that consumes valid messages."""
    with patch(
        "network_data_template_app.message_bus_consumer.get_nr_cell_dus",
        new_callable=AsyncMock,
    ) as mock_get_nr_cell_dus:
        mock_get_nr_cell_dus.return_value = get_topology_get_nr_cell_dus_response
        consumer_instance = MessageBusConsumer(
            sync_oauth_client, async_oauth_client, kafka_consumer_with_valid_messages
        )
        await consumer_instance._fetch_prefixed_fdns()
        yield consumer_instance


@pytest.fixture
def message_bus_consumer_consumes_err_messages(
    sync_oauth_client, async_oauth_client, kafka_consumer_with_err_messages
):
    """MessageBusConsumer that consumes error messages."""
    consumer_instance = MessageBusConsumer(
        sync_oauth_client, async_oauth_client, kafka_consumer_with_err_messages
    )
    yield consumer_instance


@pytest.fixture
def message_bus_consumer_with_kafka_exception(
    sync_oauth_client, async_oauth_client, kafka_consumer_raises_kafka_exception
):
    """MessageBusConsumer that raises KafkaException."""
    consumer_instance = MessageBusConsumer(
        sync_oauth_client, async_oauth_client, kafka_consumer_raises_kafka_exception
    )
    yield consumer_instance


@pytest_asyncio.fixture
async def mock_logger(no_log_certs):
    logger = _MTLSLogger(
        console_logger=_ConsoleLogger("network-data-template-app-test", Severity.DEBUG)
    )
    logger.client = httpx.AsyncClient()
    logger.log_queue = asyncio.Queue()
    yield logger
    logger.log_queue.empty()


@pytest.fixture()
def log_control_file():
    os.environ["LOG_CTRL_FILE"] = "non-empty-path-string"
    yield
    os.environ["LOG_CTRL_FILE"] = ""


def populate_environment_variables():
    """Populate environment variables"""
    os.environ["IAM_CLIENT_ID"] = "IAM_CLIENT_ID"
    os.environ["IAM_CLIENT_SECRET"] = "IAM_CLIENT_SECRET"
    os.environ["IAM_BASE_URL"] = "https://www.iam-base-url.com"
    os.environ["CA_CERT_FILE_NAME"] = "CA_CERT_FILE_NAME"
    os.environ["CA_CERT_FILE_PATH"] = "CA_CERT_MOUNT_PATH"
    os.environ["LOG_ENDPOINT"] = "LOG_ENDPOINT"
    os.environ["APP_KEY"] = "APP_KEY"
    os.environ["APP_CERT"] = "APP_CERT"
    os.environ["APP_CERT_FILE_PATH"] = "APP_CERT_FILE_PATH"
    os.environ["KAFKA_CERT_FILE_PATH"] = "KAFKA_CERT_FILE_PATH"
    os.environ["CONSUMER_MESSAGE_BATCH_SIZE"] = "1"
    os.environ["CONSUMER_TIMEOUT"] = "1.0"
    os.environ["CONTAINER_NAME"] = "test-container-name"
