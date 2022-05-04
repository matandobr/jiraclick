# Edit these parameters
# JIRA parameters
JIRA_API = ''
JIRA_MAIL = r''
JIRA_URL = r'https://COMPANY.atlassian.net/'
JIRA_PROJECT = 'RES'
# Clickup parameters
CLICKUP_API = ''
CLICKUP_TEAM = ''
CLICKUP_SPACE = ''
CLICKUP_PROJECT = 'Task management'
CLICKUP_DEFAULT_LIST = 'Other'

# Optional parameters

# Use this as default priority for tasks imported from Jira
DEFAULT_CLICKUP_PRIORITY = 1  # 1 Is urgent
DB_PATH = r'db.json'

# Mappings between JIRA to ClickUp - Might change from environment to environment
JIRA_TO_CLICKUP_STATUS = {
    'TO DO': 'OPEN',
    'HOLD': 'HOLD',
    'IN PROGRESS': 'IN PROGRESS',
    'REVIEW': 'REVIEW',
    'DONE': 'CLOSED'
}

# ClickUp priorities are: 1 is Urgent, 2 is High, 3 is Normal, 4 is Low
JIRA_TO_CLICKUP_PRIORITY = {
    'Lowest': 4,
    'Low': 4,
    'Medium': 3,
    'High': 2,
    'Highest': 1
}

