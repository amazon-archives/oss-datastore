# OSS-Datastore
The goal of this package is to gather data from GitHub via API calls, from both v3 and v4 APIs, and then store said data for further analysis in a data warehouse.

## Goals
GitHub doesn't keep information around indefinitely but for a short amount of time, usually around 14 days worth of data. Because of this, it is difficult to track information around your GitHub organizations (orgs) and repositories (repos) for planning the best place to focus your time/resources. This is exacerbated by the fact that requests to the GitHub APIs are finicky when asking for multiple large sets of data and can get your IP address blocked from making API requests for a period of time.

To get around this, the OSS-Datastore establishes a pipeline for ingesting data from the GitHub APIs, runs ETL (extract/transform/load) operations, store data into Redshift using the [data vault modeling](https://en.wikipedia.org/wiki/Data_vault_modeling) technique, and establish a base set of information/data marts for end user analysis and consumption. This modeling technique moves data from multiple sources to a staging area, ETL actions store that data into the data vault, and the data is then spun out into infomarts which are where the end users actually interacts with the data. Below is a really bad diagram to demonstrate the flow of data through the system.

![overview](docs/images/GH_Data_Vault_Overview.jpg)

Items that will be tracked include:

* Stars/forks/watchers
* Repo traffic/stats
* Issue metrics
* Pull request activity
  * New pull requests
  * replies or updates required
* Tracking user (member and external colalborator) access levels
* Security issues in a repo and its dependencies

This isn't the definitive list of information that will be tracked and will expand as the package grows. and the tentative data model can be found in <a href="docs/images/GH_Data_Vault_Layout.jpeg">docs/images/GH_Data_Vault_Layout.jpeg</a>

## Setup
You need to have pipenv installed locally

> `pip install --user pipenv`

To install new runtime dependencies 

> `pipenv install <package name>`

To install new dev dependencies 

> `pipenv install <package name> --dev`

To activate shell:

> `pipenv shell`

Ensure you have filled out the information in Config.py and run

> `pipenv run python datastore.py`

## Development tracker
* [ ] Staging area work
   * [ ] request and locally store information for the following
     * [ ] [repo information](https://developer.github.com/v4/object/repository/) including active CVEs
     * [ ] [team information](https://developer.github.com/v4/object/team/)
     * [ ] [user information](https://developer.github.com/v4/object/user/)
   * [ ] Dead letter queue for failed data requests in PostgreSQL
     * [X] Define schema
     * [X] Store data when requests fail
     * [ ] Monitoring and alerting on dead letter queue
   * [ ] Cron job to kick-off new data requests
* [ ] Refine <a href="docs/images/GH_Data_Vault_Layout.jpeg">data vault model</a>
* [ ] Data warehouse construction via AWS Cloudformation
    * [ ] Define and build the hubs
    * [ ] Define and build the links
    * [ ] Define and build the satellites
    * [ ] Define and build the metrics vault
    * [ ] Define and build the business vault
* [ ] ETL functionality
  * [ ] Staging to dead letter queue
  * [ ] Staging to data vault
  * [ ] Staging to long term storage in Amazon S3
* [ ] Initial data/info mart construction via AWS Cloudformation
  * [ ] Data exploration via Amazon QuickSight

## License
This library is licensed under the Apache 2.0 License.
