"""
FastAPI Application for Network Data Service.
This script should not be run standalone.
In order to run the application, pass the app instance to an ASGI server.
"""

from contextlib import asynccontextmanager

from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

from .message_bus_consumer import MessageBusConsumer, start_message_bus_consumer
from .mtls_logging import logger
from .oauth import oauth, synchronous_oauth
from .routes import api_router, healthcheck_router
from .report_generator import ReportGenerator


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """
    Async context manager for FastAPI application lifespan.
    This function is used to set up and clean up resources during the application's lifecycle.
    It runs before the application starts and after it shuts down.

    Yields:
        None: Allows the application to run while resources remain active.
    """
    await logger.start_log_sender()
    logger.info("Starting up Network Data Template App...")
    await oauth.setup_client()
    synchronous_oauth.setup_client()
    synchronous_client = synchronous_oauth.get_oauth_client()
    asynchronous_client = await oauth.get_oauth_client()
    message_bus_consumer = MessageBusConsumer(synchronous_client, asynchronous_client)

    consumer_task = await start_message_bus_consumer(message_bus_consumer)

    report_generator = ReportGenerator(asynchronous_client)
    report_generator.start_schedule(trigger="interval", minutes=15)

    fastapi_app.state.is_ready = True
    logger.info("Network Data Template App is now ready")

    yield
    fastapi_app.state.is_ready = False
    logger.info("Network Data Template App is shutting down.")

    report_generator.stop_schedule()
    consumer_task.cancel()
    await oauth.close_client()
    synchronous_oauth.close_client()


app = FastAPI(
    title="Network Data Template App",
    description="An example app serving as a reference point for how an rApp can be developed to work with the platform capabilities.",
    version="1.0.1",
    license={
        "name": "COPYRIGHT Ericsson 2025",
        "url": "https://www.ericsson.com/en/legal",
    },
    termsOfService="https://www.ericsson.com/en/legal",
    lifespan=lifespan,
    openapi_url=None,  # disable generation of OpenAPI documentation
)

app.state.is_ready = False

app.include_router(api_router)
app.include_router(healthcheck_router, prefix="/network-data-template-app/health")
