"""
This module provides a Prometheus Metrics Registry with counters.
"""

from prometheus_client import (
    CollectorRegistry,
    Counter,
    disable_created_metrics,
    generate_latest,
)
from .mtls_logging import logger, Severity

SERVICE_PREFIX = "network_data_template_app"


class MetricsRegistry(CollectorRegistry):
    """
    Implementation of Prometheus Client's CollectorRegistry.
    """

    def __init__(self):
        super().__init__()
        disable_created_metrics()
        self.counters = self._create_metrics()
        self._register_counters()

    def _create_metrics(self) -> dict[str, Counter]:
        counters = {}
        # Create network configuration counters
        counters["network_configuration_successful_requests"] = Counter(
            namespace=SERVICE_PREFIX,
            name="network_configuration_successful_requests",
            documentation="Total number of successful network-configuration API requests",
        )
        counters["network_configuration_failed_requests"] = Counter(
            namespace=SERVICE_PREFIX,
            name="network_configuration_failed_requests",
            documentation="Total number of network-configuration API request failures",
        )

        # Create topology counters
        counters["topology_successful_requests"] = Counter(
            namespace=SERVICE_PREFIX,
            name="topology_successful_requests",
            documentation="Total number of successfull topology API requests",
        )
        counters["topology_failed_requests"] = Counter(
            namespace=SERVICE_PREFIX,
            name="topology_failed_requests",
            documentation="Total number of topology API request failures",
        )

        return counters

    def _register_counters(self) -> None:
        for counter in self.counters.values():
            self.register(counter)
        logger.debug(
            f"Created metrics registry in format:\n{generate_latest(self).decode('utf-8')}"
        )

    def _unregister_counters(self) -> None:
        for counter in self.counters.values():
            self.unregister(counter)
        self.counters = {}


metrics_registry = MetricsRegistry()
