import datetime
import logging
import os
import time

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.mgmt.rdbms.mysql_flexibleservers import MySQLManagementClient

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector import errorcode

# Load monitoring configurations.
subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
resource_group = os.getenv('DB_RESOURCE_GROUP')
server_name = os.getenv('DB_SERVER_NAME')
admin_name = os.getenv('DB_ADMIN_NAME')
admin_password = os.getenv('DB_ADMIN_PASSWORD')

# Acquire a credential object using default authentication.
try:
    credential = DefaultAzureCredential()
    mysql_client = MySQLManagementClient(credential, subscription_id)
    server = mysql_client.servers.get(resource_group, server_name)
except:
    logging.error(f'Fail to find {server_name} in subscription {subscription_id} and resource group {resource_group} ' +
                  'with default credential. Please check your configurations.')
    raise

# Create a connection with configurations provided.
connection = MySQLConnection()
connection.config(
    host=server.fully_qualified_domain_name,
    user=admin_name,
    password=admin_password
)
is_healthy = True
logging.info(f'Monitoring MySQL flexible server {server.name}.')


def check_connection() -> bool:
    retry_connection = True
    tls_error_retry_count = 0

    while retry_connection:
        retry_connection = False
        try:
            logging.info('Establishing new connection...')
            timestamp = time.perf_counter()
            connection.connect()
            logging.info(
                f'Establish new connection taken {time.perf_counter() - timestamp} Seconds.')
        except mysql.connector.Error as err:
            if 2000 <= err.errno <= 2999:
                # If the failure is TLS error, we will retry immedeiately, but up to three times.
                if tls_error_retry_count < 3:
                    retry_connection = True
                    tls_error_retry_count += 1
                    logging.warning(
                        f'Immediately retry the TLS connection failure. Count: {tls_error_retry_count}.')
                else:
                    return False
            else:
                # There's a problem in provided credential or permissions.
                logging.error(f'ERROR {err.errno} ({err.sqlstate}): {err.msg}')
                exit()
    return True


def main(timer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()
    logging.info(f'Python timer trigger function ran at {utc_timestamp}.')

    if timer.past_due:
        logging.info('The timer is past due!')
        return

    global is_healthy
    if check_connection():
        logging.info(f'Server {server_name}: Available.')
        is_healthy = True
    else:
        logging.warning(f'Server {server_name}: Unavailable.')
        if is_healthy:
            # Failover only if the server was available before this execution.
            try:
                mysql_client.servers.begin_failover(resource_group, server_name)
                logging.warning(f'Server {server_name}: Failover accepted.')
            except:
                logging.warning(f'Server {server_name}: Failover interrupted.')
        is_healthy = False
