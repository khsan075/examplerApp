"""
This module provides functionality to interact with the 'Topology & Inventory' capability
and retrieve NRCellDU entities and their source IDs.

More details: [Topology & Inventory](https://developer.intelligentautomationplatform.ericsson.net/#capabilities/topology-inventory)

Modules:
- requests: To make HTTP requests.
- config: Retrieves configuration settings.
"""

from authlib.integrations.httpx_client import AsyncOAuth2Client

from .mtls_logging import logger
from .config import get_config


async def get_nr_cell_dus(
    client: AsyncOAuth2Client, limit=10
) -> list[dict[str, object]]:
    """
    Retrieve NRCellDU entities.

    Args:
        session (OAuth2Session): The OAuth2Session for API requests.

    Raises:
        HTTPError: If an error occurs in fetching NRCellDU entities.
    """
    # Construct Authorization header for the request

    # Build URL for request
    topology_and_inventory_base_url = (
        get_config()["iam_base_url"] + "/topology-inventory/v1alpha11"
    )

    url = f"{topology_and_inventory_base_url}/domains/RAN/entities?targetFilter=/NRCellDU/sourceIds&limit={limit}"

    logger.debug(f"Getting cells from {url}")

    # Perform the GET request to fetch entities
    response = await client.request("GET", url)

    # Raise an exception for bad responses
    response.raise_for_status()

    logger.debug(
        f"Retrieved {len(response.json()['items'])} items from Topology & Inventory"
    )

    return response.json()["items"]


def get_sourceids_from_cells(cells: list[dict[str, object]]) -> list[str]:
    """
    Extract a list of source IDs from NRCellDU entities.

    Args:
        cells (list[dict]): The list of NRCellDU entities.
    """
    source_ids = []
    for cell in cells:
        for source_id in cell["o-ran-smo-teiv-ran:NRCellDU"][0]["sourceIds"]:
            if source_id.startswith("urn:3gpp:dn:"):
                source_ids.append(source_id)
                logger.debug(f"Source ID obtained from cell:\n{cell}")
                break
        else:
            logger.debug(f"No source ID obtained from cell:\n{cell}")
    logger.debug(f"Obtained {len(source_ids)} source IDs")
    return source_ids
