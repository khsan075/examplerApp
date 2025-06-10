from datetime import datetime, timezone
from operator import countOf

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .message_bus_consumer import fdn_to_pm_counter_status
from .mtls_logging import logger
from .network_configuration import get_attributes_for_source_ids


class ReportGenerator:
    """
    Collect FDNs, attributes and counters and provide a readable tabular representation of what was collected.
    `clear_data_upon_usage` can be disabled for testing.
    """

    MISFIRE_GRACE_TIME_SECONDS = 60  # This allows extra time for the logging job to complete in case of any network delays

    def __init__(
        self,
        async_oauth_client,
        attribute="operationalState",
        clear_data_upon_usage=True,
    ):
        self.async_oauth_client = async_oauth_client
        self.attribute = attribute
        self.clear_data_upon_usage = clear_data_upon_usage
        self.scheduler = AsyncIOScheduler()

    async def __get_report_data(self) -> list[str]:
        """
        Parse the `fdn_to_pm_counter_status` dict for the FDN and counter status, then make a call to Network Configuration to retrieve
        the `attribute` value to populate the report.
        """
        cached_dict = dict(sorted(fdn_to_pm_counter_status.items()))
        if self.clear_data_upon_usage:
            for key in fdn_to_pm_counter_status.keys():
                fdn_to_pm_counter_status[key] = False
        report_data = []
        source_id_attribute_map = await get_attributes_for_source_ids(
            self.async_oauth_client, list(cached_dict.keys()), self.attribute
        )

        for source_id in source_id_attribute_map:
            fdn = source_id.get("id")
            attribute = source_id.get(self.attribute)
            counters = cached_dict[fdn]
            report_data.append(
                f"fdn={fdn}; {self.attribute}={attribute or 'UNKNOWN'}; countersCollected={counters}"
            )
        return report_data

    async def __log_message(self):
        """Log a message with FDNs, attribute value and counter collection status."""
        counters_collected = countOf(fdn_to_pm_counter_status.values(), True)
        report_data = await self.__get_report_data()
        log_string = ""
        for row in report_data:
            log_string += f"{row}\n"
        logger.info(
            (
                f"Collected PM counters for {counters_collected} out of {len(report_data)} NRCellDUs between {self.period_start.strftime('%H:%M')} and {self.period_end.strftime('%H:%M')} (UTC):\n{log_string}"
            )
        )
        self.period_start = self.period_end
        self.period_end = self.log_job.next_run_time.astimezone(timezone.utc)
        logger.info(f"Next report at {self.period_end.strftime('%H:%M')} (UTC)")

    def start_schedule(self, trigger, *args, **kwargs):
        """Log the report at a regular interval. Any args given are passed directly into APScheduler's `add_job`."""
        logger.debug("Starting report logging schedule.")
        self.log_job = self.scheduler.add_job(
            self.__log_message,
            trigger=trigger,
            max_instances=1,
            replace_existing=True,
            misfire_grace_time=self.MISFIRE_GRACE_TIME_SECONDS,
            *args,
            **kwargs,
        )
        self.scheduler.start()
        self.period_start = datetime.now(timezone.utc)
        self.period_end = self.log_job.next_run_time.astimezone(timezone.utc)
        logger.info(
            f"Report scheduler started - next report at {self.period_end.strftime('%H:%M')} (UTC)"
        )

    def stop_schedule(self):
        """Shut down the scheduler."""
        self.scheduler.shutdown()
