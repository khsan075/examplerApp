"""This module handles environment variables"""

import os


# pylint: disable=too-many-locals
def get_config() -> dict[str, str]:
    """Extract configuration from environment variables."""
    iam_client_id = get_os_env_string("IAM_CLIENT_ID", "")
    iam_client_secret = get_os_env_string("IAM_CLIENT_SECRET", "")
    iam_base_url = get_os_env_string("IAM_BASE_URL", "")
    ca_cert_file_name = get_os_env_string("CA_CERT_FILE_NAME", "")
    ca_cert_file_path = get_os_env_string("CA_CERT_FILE_PATH", "")
    log_ctrl_file = get_os_env_string("LOG_CTRL_FILE", "")
    log_endpoint = get_os_env_string("LOG_ENDPOINT", "")
    app_key = get_os_env_string("APP_KEY", "")
    app_cert = get_os_env_string("APP_CERT", "")
    app_cert_file_path = get_os_env_string("APP_CERT_FILE_PATH", "")
    kafka_cert_file_path = get_os_env_string(
        "KAFKA_CERT_MOUNT_PATH", ""
    ) + get_os_env_string("KAFKA_CERT_FILE_NAME", "")
    max_retries = get_os_env_string("MAX_RETRIES", "5")
    retry_delay = get_os_env_string("RETRY_DELAY", "5")
    consumer_message_batch_size = validate_type(
        "CONSUMER_MESSAGE_BATCH_SIZE", int, "1000"
    )
    consumer_timeout = validate_type("CONSUMER_TIMEOUT", float, "1.0")

    config = {
        "service_name": "rapp-eric-oss-network-data-template-app",
        "iam_client_id": iam_client_id,
        "iam_client_secret": iam_client_secret,
        "iam_base_url": iam_base_url,
        "ca_cert_file_name": ca_cert_file_name,
        "ca_cert_file_path": ca_cert_file_path,
        "log_ctrl_file": log_ctrl_file,
        "log_endpoint": log_endpoint,
        "app_key": app_key,
        "app_cert": app_cert,
        "app_cert_file_path": app_cert_file_path,
        "kafka_cert_file_path": kafka_cert_file_path,
        "max_retries": max_retries,
        "retry_delay": retry_delay,
        "consumer_message_batch_size": consumer_message_batch_size,
        "consumer_timeout": consumer_timeout,
    }
    return config


def validate_type(env_variable, expected_type, default):
    """
    Validates if the given value is of the expected type.
    If not, returns the default value.
    """
    try:
        value = get_os_env_string(env_variable, "")
        if expected_type == int:
            return int(value)
        if expected_type == float:
            return float(value)
        raise TypeError("Unsupported type for validation")
    except (ValueError, TypeError):
        return default


def get_os_env_string(env_name: str, default_value: str) -> str:
    """Return the value for a given environment variable."""
    return os.getenv(env_name, default_value).strip()
