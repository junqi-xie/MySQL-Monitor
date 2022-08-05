# MySQLMonitor - Azure Function App

This Azure Function App works as a monitor for [Azure Database for MySQL - Flexible Server](https://docs.microsoft.com/en-us/azure/mysql/flexible-server/) with [High availability](https://docs.microsoft.com/en-us/azure/mysql/flexible-server/concepts-high-availability) enabled. It detects networking issues between the database server and the customer networking endpoint, and triggers a forced failover on behalf of the customer. It mitigates the limitations in the automatic failover detection mechanism.

The monitor is designed to run as an [Azure Function App](https://docs.microsoft.com/en-us/azure/azure-functions/), but you can also run it locally.

## Getting Started

Note: If you are using VS Code, you can also refer to [this tutorial](https://docs.microsoft.com/en-us/azure/azure-functions/create-first-function-vs-code-python).

### Deploy in Azure

1. Clone the repository.
2. Create the function app in Azure.
   * For the monitor to function properly, please choose the same district as your application (not your database server).
3. Deploy the project to Azure.
4. Configure a [Managed Identity](https://docs.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/) for this app.
   * You must assign Read and Failover permissions for MySQL Flexible to the identity.
5. Configure the following App Settings:
   * `AZURE_SUBSCRIPTION_ID`: The subscription ID of the server.
   * `DB_RESOURCE_GROUP`: The resource group of the server.
   * `DB_SERVER_NAME`: The name of the server.
   * `DB_ADMIN_NAME`: The name of the login credential.
   * `DB_ADMIN_PASSWORD`: The password of the login credential.
6. Start the function app. Now it's ready to monitor your database server.

### Deploy locally

1. Clone the repository.
2. Install the following dependencies:
   * [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local#install-the-azure-functions-core-tools) version 3.x
   * Python versions that are [supported by Azure Functions](https://docs.microsoft.com/en-us/azure/azure-functions/supported-languages#languages-by-runtime-version).
   * [Visual Studio Code](https://code.visualstudio.com/) on one of the [supported platforms](https://code.visualstudio.com/docs/supporting/requirements#_platforms).
   * The [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) for Visual Studio Code.
   * The [Azure Functions extension](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-azurefunctions) for Visual Studio Code.
3. Open the repository in VS Code.
4. Configure the environment variables as stated above.
5. Start debugging, and you are good to go.

## How it works

The monitor will use the credential you provide to ping the MySQL flexible server. When it fails to connect the server, it'll retry 3 times if it encounters a TLS error. If the server is still not responding, it'll begin a forced failover, in the hope to activate the standby.

Note that the monitor will not begin a new failover process before it connects to the server successfully once. Please check your firewall rules, so that the monitor will not mistakenly consider the server as unavailable.

You can change the running schedule in `function.json`. The default value for the running schedule is `*/5 * * * * *`, which means to execute the function every 5 seconds. Please refer to [cron expression](https://en.wikipedia.org/wiki/Cron#CRON_expression) for full details if you would like to change the schedule.

## Learn more

* [Azure Database for MySQL - Flexible Server](https://docs.microsoft.com/en-us/azure/mysql/flexible-server/)
* [High availability concepts](https://docs.microsoft.com/en-us/azure/mysql/flexible-server/concepts-high-availability)
* [Azure Functions](https://docs.microsoft.com/en-us/azure/azure-functions/)
* [Cron expression](https://en.wikipedia.org/wiki/Cron#CRON_expression) for Timer Triggers in Azure Functions.
