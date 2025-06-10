# pylint: disable=W0613
# W0613: Unused argument
"""Tests which cover the routes of the application"""

import json


def test_get_root_returns_bad_response(client):
    """
    GET to "/"
    400 Bad Request
    """
    response = client.get("/network-data-template-app/")
    assert response.status_code == 400


def test_get_topology_returns_topology(client):
    """
    GET to "/topology"
    200 OK
    Body "{topology response}"
    """
    response = client.get("/network-data-template-app/topology")
    with open(
        "./tests/topology_response.json",
        "r",
        encoding="utf-8",
    ) as f:
        expected_response_json = json.load(f)
        response_json = json.loads(response.text)
        assert [response_json, response.status_code] == [
            expected_response_json["items"],
            200,
        ]


def test_get_network_configuration_returns_network_configuration(client):
    """
    GET to "/network-configuration"
    200 OK
    Body "{ncmp response}"
    """
    source_ids_enabled = [
        "urn:3gpp:dn:SubNetwork=Europe,SubNetwork=Ireland,MeContext=NR01gNodeBRadio00046,ManagedElement=NR01gNodeBRadio00046,GNBDUFunction=1,NRCellDU=NR01gNodeBRadio00046-2",
        "urn:3gpp:dn:SubNetwork=Europe,SubNetwork=Ireland,MeContext=NR01gNodeBRadio00047,ManagedElement=NR01gNodeBRadio00047,GNBDUFunction=1,NRCellDU=NR01gNodeBRadio00047-2",
    ]

    source_ids_disabled = [
        "urn:3gpp:dn:SubNetwork=Europe,SubNetwork=Ireland,MeContext=NR01gNodeBRadio00041,ManagedElement=NR01gNodeBRadio00041,GNBDUFunction=1,NRCellDU=NR01gNodeBRadio00041-1",
        "urn:3gpp:dn:SubNetwork=Europe,SubNetwork=Ireland,MeContext=NR01gNodeBRadio00042,ManagedElement=NR01gNodeBRadio00042,GNBDUFunction=1,NRCellDU=NR01gNodeBRadio00042-1",
        "urn:3gpp:dn:SubNetwork=Europe,SubNetwork=Ireland,MeContext=NR01gNodeBRadio00043,ManagedElement=NR01gNodeBRadio00043,GNBDUFunction=1,NRCellDU=NR01gNodeBRadio00043-1",
        "urn:3gpp:dn:SubNetwork=Europe,SubNetwork=Ireland,MeContext=NR01gNodeBRadio00044,ManagedElement=NR01gNodeBRadio00044,GNBDUFunction=1,NRCellDU=NR01gNodeBRadio00044-1",
        "urn:3gpp:dn:SubNetwork=Europe,SubNetwork=Ireland,MeContext=NR01gNodeBRadio00045,ManagedElement=NR01gNodeBRadio00045,GNBDUFunction=1,NRCellDU=NR01gNodeBRadio00045-1",
        "urn:3gpp:dn:SubNetwork=Europe,SubNetwork=Ireland,MeContext=NR01gNodeBRadio00046,ManagedElement=NR01gNodeBRadio00046,GNBDUFunction=1,NRCellDU=NR01gNodeBRadio00046-1",
        "urn:3gpp:dn:SubNetwork=Europe,SubNetwork=Ireland,MeContext=NR01gNodeBRadio00046,ManagedElement=NR01gNodeBRadio00046,GNBDUFunction=1,NRCellDU=NR01gNodeBRadio00046-3",
        "urn:3gpp:dn:SubNetwork=Europe,SubNetwork=Ireland,MeContext=NR01gNodeBRadio00047,ManagedElement=NR01gNodeBRadio00047,GNBDUFunction=1,NRCellDU=NR01gNodeBRadio00047-1",
    ]
    expected_response = [
        {"id": source_id, "operationalState": "DISABLED"}
        for source_id in source_ids_disabled
    ]
    expected_response.extend(
        [
            {"id": source_id, "operationalState": "ENABLED"}
            for source_id in source_ids_enabled
        ]
    )
    response = client.get("/network-data-template-app/network-configuration")
    response_json = json.loads(response.text)
    assert [
        sorted(response_json, key=lambda item: item["id"]),
        response.status_code,
    ] == [sorted(expected_response, key=lambda item: item["id"]), 200]


def test_get_network_configuration_returns_400(client):
    """
    GET to "/network-configuration?attribute=invalid"
    400 Bad Request
    Body containing error message
    """
    expected_response = {
        "Error": "Invalid attribute: invalid. Allowed attributes are ['administrativeState', 'operationalState']"
    }
    response = client.get(
        "/network-data-template-app/network-configuration?attribute=invalid"
    )
    response_json = json.loads(response.text)
    assert [response_json, response.status_code] == [expected_response, 400]


def test_get_metrics_returns_metrics(client):
    """
    GET to "/metrics"
    200 OK
    Body containing Prometheus-compatible metrics
    """
    response = client.get("/network-data-template-app/metrics")
    assert response.status_code == 200
    assert (
        "network_data_template_app_network_configuration_successful_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_network_configuration_failed_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_successful_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_failed_requests_total 0.0" in response.text
    )


def test_metrics_does_not_expose_created(client):
    """
    GET to "/metrics"
    200 OK
    Body does not contain _created gauges for Prometheus-compatible metrics
    """
    response = client.get("/network-data-template-app/metrics")
    assert response.status_code == 200
    assert "_created" not in response.text


def test_topology_metrics_successfully_increments(client):
    """
    GET to "/metrics"
    200 OK
    Body containing metrics which have incremented by 1
    """
    response = client.get("/network-data-template-app/metrics")
    assert (
        "network_data_template_app_network_configuration_successful_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_network_configuration_failed_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_successful_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_failed_requests_total 0.0" in response.text
    )
    client.get("/network-data-template-app/topology")
    response = client.get("/network-data-template-app/metrics")
    assert response.status_code == 200
    assert (
        "network_data_template_app_network_configuration_successful_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_network_configuration_failed_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_successful_requests_total 1.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_failed_requests_total 0.0" in response.text
    )


def test_network_configuration_metrics_successfully_increments(client):
    """
    GET to "/metrics"
    200 OK
    Body containing metrics which have incremented by 1
    """
    response = client.get("/network-data-template-app/metrics")
    assert response.status_code == 200
    assert (
        "network_data_template_app_network_configuration_successful_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_network_configuration_failed_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_successful_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_failed_requests_total 0.0" in response.text
    )

    client.get("/network-data-template-app/network-configuration")

    response = client.get("/network-data-template-app/metrics")
    assert response.status_code == 200
    assert (
        "network_data_template_app_network_configuration_successful_requests_total 1.0"
        in response.text
    )
    assert (
        "network_data_template_app_network_configuration_failed_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_successful_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_failed_requests_total 0.0" in response.text
    )


def test_metrics_successfully_increment_on_failure(client, no_platform_access):
    """
    GET to "/metrics"
    200 OK
    Body containing metrics which have incremented by 1
    """
    response = client.get("/network-data-template-app/metrics")
    assert response.status_code == 200
    assert (
        "network_data_template_app_network_configuration_successful_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_network_configuration_failed_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_successful_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_failed_requests_total 0.0" in response.text
    )

    client.get("/network-data-template-app/topology")
    client.get("/network-data-template-app/network-configuration")

    response = client.get("/network-data-template-app/metrics")
    assert response.status_code == 200
    assert (
        "network_data_template_app_network_configuration_successful_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_network_configuration_failed_requests_total 1.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_successful_requests_total 0.0"
        in response.text
    )
    assert (
        "network_data_template_app_topology_failed_requests_total 1.0" in response.text
    )


def test_get_health_returns_health_check(client):
    """
    GET to "/health"
    200 OK
    Body "Ok\n"
    """
    response = client.get("/network-data-template-app/health/liveness")
    expected_response = json.loads(
        '{"healthy":true,"checks":[{"name":"server","passed":true,"details":null}]}'
    )
    assert [response.json(), response.status_code] == [expected_response, 200]
    response = client.get("/network-data-template-app/health/readiness")
    assert [response.json(), response.status_code] == [expected_response, 200]
