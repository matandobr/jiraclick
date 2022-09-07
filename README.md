## JiraClick
### Overview
This is a simple python script that syncs "1-1" a JIRA project to a ClickUp project. which means:
* Any JIRA task that is created, will also be created in ClickUp and vice versa
* If a ClickUp task status is changed, it will also be changed in JIRA - and vice versa
* The content of the task in ClickUP will be the same as its JIRA twin

### Configurations
Edit conf.py and provide the following consts - 

JIRA_API = 'EpWasdna6D8X666658'

JIRA_MAIL = r'user@mycompany.com'

JIRA_URL = r'https://mycompany.atlassian.net/'

JIRA_PROJECT = 'ABC'  # Project KEY

CLICKUP_API = 'ab_13513_Q6TASDASDASDFLT9ASDMCG'

CLICKUP_TEAM = 'MY_COMPANY'

CLICKUP_SPACE = 'My team space name'

CLICKUP_PROJECT = 'Task management'

CLICKUP_DEFAULT_LIST = 'Other' # Tasks imported from JIRA will be created here


### How to run it
* Tested with python 3.8
* Edit conf.py and edit the required parameters
* pip install -r requirements.txt
* python main.py  # Run once
* python main.py 20  # Run forever with 20 minutes sleep

### Current features
* Syncs JIRA (cloud) project/board with ClickUp project 
* Local DB to save the current state of the sync, any by that fixing endless loops
* Status update in both directions
* Content/Description copy between the two projects

### TODO
Features:
* Support links and attachments

Code:
* Improve logging
* Add tests


### Changelog
* 1.1 - Added due date & better time sync between the systems
* 1.0 - Initial release