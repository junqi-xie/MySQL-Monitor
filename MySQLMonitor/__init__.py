import datetime
import logging
import os
import time

import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.mgmt.rdbms.mysql_flexibleservers import MySQLManagementClient
from azure.communication.email import EmailClient, EmailContent, EmailRecipients, EmailAddress, EmailMessage

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector import errorcode

# Monitoring configurations.
subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')
resource_group = os.getenv('DB_RESOURCE_GROUP')
server_name = os.getenv('DB_SERVER_NAME')
admin_name = os.getenv('DB_ADMIN_NAME')
admin_password = os.getenv('DB_ADMIN_PASSWORD')

# Email Communication Service configurations.
connection_string = os.getenv('COMMUNICATION_CONNECTION_STRING')
sender_address = os.getenv('SENDER_ADDRESS')
recipient_address = os.getenv('RECIPIENT_ADDRESS')

# Global parameters.
MAX_TLS_ERROR_RETRY = 3

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
tls_error_retry_count = 0
logging.info(f'Monitoring MySQL flexible server {server.name}.')


def check_connection() -> bool:
    try:
        logging.info('Establishing new connection...')
        timestamp = time.perf_counter()
        connection.connect()
        logging.info(
            f'Establish new connection taken {time.perf_counter() - timestamp} Seconds.')
        return True
    except mysql.connector.Error as err:
        if 2000 <= err.errno <= 2999:
            return False
        else:
            # There's a problem in provided credential or permissions.
            logging.error(f'ERROR {err.errno} ({err.sqlstate}): {err.msg}')
            exit()


def send_email(server_name: str, utc_timestamp: str) -> None:
    if not connection_string or not sender_address or not recipient_address:
        # Email Communication Service is not configured.
        return

    # Create the email message
    email_client = EmailClient.from_connection_string(connection_string)
    content = EmailContent(
        subject='Azure Database for MySQL Monitor Alert',
        plain_text=f'Your server {server_name} began a failover process due to an ongoing connection failure at {utc_timestamp}.',
        html=f'<html><p>Your server <b>{server_name}</b> began a failover process due to an ongoing connection failure ' +
             f'at <b>{utc_timestamp}</b>.</p></html>',
    )
    recipients = EmailRecipients(
        to=[EmailAddress(email=recipient_address)]
    )
    message = EmailMessage(
        sender=sender_address,
        content=content,
        recipients=recipients
    )

    try:
        # Send the email message
        response = email_client.send(message)
        logging.info(
            f'Email alert sent to {recipient_address} with ID {response.message_id}.')
    except:
        logging.warning(
            f'Email alert configuration error. Please check your configurations.')
        pass


def main(timer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()
    logging.info(f'Python timer trigger function ran at {utc_timestamp}.')

    if timer.past_due:
        logging.info('The timer is past due!')
        return

    global is_healthy, tls_error_retry_count
    if check_connection():
        logging.info(f'Server {server_name}: Available.')
        is_healthy = True
        tls_error_retry_count = 0
    else:
        logging.warning(f'Server {server_name}: Unavailable.')
        if is_healthy:
            # Check connection status if the server was in healthy state.
            if tls_error_retry_count < MAX_TLS_ERROR_RETRY:
                # Retry if the error count is within acceptable range.
                tls_error_retry_count += 1
                logging.warning(
                    f'Retry the TLS connection failure. Count: {tls_error_retry_count}.')
            else:
                # Begin failover operation.
                try:
                    mysql_client.servers.begin_failover(resource_group, server_name)
                    logging.warning(
                        f'Server {server_name}: Failover accepted.')
                    utc_timestamp = datetime.datetime.utcnow().replace(
                        tzinfo=datetime.timezone.utc).isoformat()
                    send_email(server_name, utc_timestamp)
                except:
                    logging.warning(
                        f'Server {server_name}: Failover interrupted.')
                is_healthy = False
