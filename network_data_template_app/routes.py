"""
This module defines the Network Data Template App's API routes.
The /topology and /network-configuration APIs defined here are not part of the current use case of the Example rApp,
but may be used as the use case evolves.
"""

from fastapi import APIRouter
from fastapi.responses import Response, JSONResponse
from fastapi_healthchecks.api.router import HealthcheckRouter, Probe

from prometheus_client import generate_latest

import network_data_template_app.network_configuration as ncmp
from network_data_template_app import topology_and_inventory

from .health import SimpleHealthCheck
from .metrics import metrics_registry
from .mtls_logging import logger
from .oauth import oauth

api_router = APIRouter(prefix="/network-data-template-app")

# Set up simple liveness and readiness probes.
healthcheck_router = HealthcheckRouter(
    Probe(name="liveness", checks=[SimpleHealthCheck()]),
    Probe(name="readiness", checks=[SimpleHealthCheck()]),
)


@api_router.get("/metrics", response_class=Response)
async def metrics():
    """
    This route returns Prometheus metrics in plaintext format.
    """
    return Response(generate_latest(metrics_registry), media_type="text/plain")


@api_router.get("/")
async def root():
    """This route returns a 400 Bad Request HTTP response."""
    logger.info("400 Bad request: User tried accessing '/network-data-template-app/'")
    return Response("400 Bad Request", 400)


@api_router.get("/topology")
async def topology():
    """
    This route returns simple topology information
    and increments the appropriate topology counter.
    """
    try:

        # Get NRCellDU entities
        client = await oauth.get_oauth_client()
        cells = await topology_and_inventory.get_nr_cell_dus(client)
        metrics_registry.counters["topology_successful_requests"].inc()
        logger.info("200 OK /topology")
        return JSONResponse(cells)
    except Exception as e:
        logger.error(f"500 Internal Server Error: An error occurred - {str(e)}")
        metrics_registry.counters["topology_failed_requests"].inc()
        return JSONResponse({"Error": "An internal server error occurred."}, 500)


@api_router.get("/network-configuration")
async def network_configuration(attribute: str = "operationalState"):
    """
    This route returns the requested attributes
    and increments the appropriate network configuration counter.
    """
    try:
        oauth_client = await oauth.get_oauth_client()
        # Get the attribute from the request query parameters (defaults to 'operationalState')
        allowed_attributes = ["administrativeState", "operationalState"]
        if attribute not in allowed_attributes:
            raise ValueError(
                f"Invalid attribute: {attribute}. Allowed attributes are {allowed_attributes}"
            )

        # Get NRCellDU entities and extract their source IDs
        cells = await topology_and_inventory.get_nr_cell_dus(oauth_client)
        ids = topology_and_inventory.get_sourceids_from_cells(cells)

        # Get attributes for the extracted source IDs (throws on failure)
        results = await ncmp.get_attributes_for_source_ids(oauth_client, ids, attribute)

        metrics_registry.counters["network_configuration_successful_requests"].inc()
        logger.info("200 OK /network-configuration")
        return JSONResponse(results, 200)
    except ValueError as e:
        # If an invalid attribute is provided, return 400
        logger.warning(f"400 Bad Request: {str(e)}")
        metrics_registry.counters["network_configuration_failed_requests"].inc()
        return JSONResponse({"Error": str(e)}, 400)
    except Exception as e:
        logger.error(f"500 Internal Server Error: An error occurred - {str(e)}")
        metrics_registry.counters["network_configuration_failed_requests"].inc()
        return JSONResponse({"Error": "An internal server error occurred."}, 500)
