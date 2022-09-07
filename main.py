import os
import sys

import jira.exceptions
from pyclickup import ClickUp
from time import sleep
from jira.client import JIRA
import json
from datetime import timedelta
from conf import *

JIRACLICK_VERSION = '1.1'


def get_key_by_value(mapping: dict, key_value):
    for key, value in mapping.items():
        if key_value == value:
            return key
    return None


# https://stackoverflow.com/a/58102506/2779402
def get_all_jira_issues(jira_client, project):
    issues = []
    i = 0
    chunk_size = 100
    while True:
        chunk = jira_client.search_issues(f'project={project}', startAt=i, maxResults=chunk_size)
        i += chunk_size
        issues += chunk.iterable
        if i >= chunk.total:
            break
    return issues


class JiraClick:
    def __init__(self, jira_api=JIRA_API, jira_mail=JIRA_MAIL, jira_url=JIRA_URL,
                 clickup_api=CLICKUP_API, jira_project=JIRA_PROJECT, db_path=DB_PATH):
        self.jira_client = JIRA(jira_url, basic_auth=(jira_mail, jira_api))
        self.clickup_client = ClickUp(clickup_api)

        # Get all jira tasks
        print('[INFO] Getting all jira issues')
        self.jira_project = jira_project
        self.all_jira_issues = get_all_jira_issues(self.jira_client, self.jira_project)

        # Get ClickUp tasks
        cu_team = next(team for team in self.clickup_client.teams if team.name == CLICKUP_TEAM)
        cu_space = next(space for space in cu_team.spaces if space.name == CLICKUP_SPACE)
        cu_project = next(project for project in cu_space.projects if project.name == CLICKUP_PROJECT)
        self.clickup_list = next(culist for culist in cu_project.lists if culist.name == CLICKUP_DEFAULT_LIST)
        print('[INFO] Getting all ClickUp tasks')
        self.all_clickup_tasks = cu_project.get_all_tasks(include_closed=True)

        self.db_path = db_path
        self.db = dict()

    def load_db(self):
        if not os.path.exists(self.db_path):
            with open(self.db_path, 'w') as fd:
                fd.write(json.dumps({}, indent=4))

        # Load previous tasks snapshot
        with open(self.db_path) as fd:
            content = fd.read()
            self.db = json.loads(content)

    def save_db(self):
        # Save current tasks snapshot
        with open(self.db_path, 'w') as fd:
            fd.write(json.dumps(self.db, indent=4))

    # returns the corresponding obj
    def search_db(self, task_id: str, jira_or_click='jira'):
        try:
            if jira_or_click == 'jira':
                return next(x for x in self.db['items'] if x['jira_key'] == task_id)
            else:
                return next(x for x in self.db['items'] if x['clickup_id'] == task_id)
        except StopIteration:
            return None

    def create_clickup_task_from_jira(self, jira_issue) -> str:
        name = f'{jira_issue.key} - {jira_issue.fields.summary}'
        content = f'Imported from JIRA - {jira_issue.key}\n\n {jira_issue.fields.description}'
        status = JIRA_TO_CLICKUP_STATUS.get(jira_issue.fields.status.name.upper()) or 'OPEN'
        priority = JIRA_TO_CLICKUP_PRIORITY.get(jira_issue.fields.priority.name) or DEFAULT_CLICKUP_PRIORITY

        # Optional fields, jira object does not support iteration or dict search...
        try:
            duedate = datetime.fromisoformat(jira_issue.fields.duedate)
        except (AttributeError, TypeError) as e:
            duedate = None

        new_clickup_id = self.clickup_list.create_task(name=name, content=content, status=status, priority=priority, due_date=duedate)
        return new_clickup_id

    def create_jira_issue_from_clickup(self, clickup_task) -> str:
        summary = f'ClickUp - {clickup_task.name}'
        description = clickup_task.description or ''
        description = f'Imported from ClickUp - {clickup_task.id}\n\n {description}'
        status = get_key_by_value(JIRA_TO_CLICKUP_STATUS, clickup_task.status.status.upper()) or 'TO DO'

        # Optional fields
        clickup_priority = clickup_task.priority
        priority = get_key_by_value(JIRA_TO_CLICKUP_PRIORITY, int(clickup_priority['id'])) if clickup_priority else None
        due_date = clickup_task.due_date or None

        list_name = clickup_task.list['name'].replace(' ', '_')

        issue_dict = {
            'project': self.jira_project,
            'summary': summary,
            'description': description,
            'issuetype': {'name': 'Task'},
            'labels': [list_name],
        }
        if clickup_priority:
            issue_dict['priority'] = {'name': priority}
        if due_date:
            issue_dict['due_date'] = due_date
        new_issue = self.jira_client.create_issue(fields=issue_dict)

        try:
            self.jira_client.transition_issue(new_issue.id, status)  # Jira won't let you set status right away
        except jira.exceptions.JIRAError as je:
            print(f'Error in status transition - {je}')

        return new_issue.key

    # Reuse the all already queried tasks + issues
    def search_task_or_issue(self, key, jira_or_click='jira'):
        try:
            if jira_or_click == 'jira':
                return next(x for x in self.all_jira_issues if x.key == key)
            else:
                return next(x for x in self.all_clickup_tasks if x.id == key)
        except StopIteration:
            return None

    # Main function for syncing Jira and ClickUp sync
    def sync(self):
        now_datetime = datetime.now()

        # Starting with Jira issues
        for jira_issue in self.all_jira_issues:
            break
            jira_issue_key = jira_issue.key  # RES-382
            existing_issue_in_db = self.search_db(jira_issue_key)

            # If the issue exist, only check for timestamp, and update clickup for any changes
            if existing_issue_in_db:
                jira_last_update = jira_issue.fields.updated
                jira_last_update = jira_last_update[:jira_last_update.find('+')]  # Small fix for jira date
                jira_last_update = datetime.fromisoformat(jira_last_update)
                db_last_update = datetime.fromisoformat(existing_issue_in_db['last_update'])
                if jira_last_update > db_last_update:
                    existing_clickup_task = self.search_task_or_issue(existing_issue_in_db['clickup_id'], 'ClickUp')
                    if not existing_clickup_task:
                        print('ERROR! Task does not exist in all_clickup_tasks even though in the db')
                        continue
                    # Gets jira and ClickUp status in the ClickUps standard
                    jira_status = JIRA_TO_CLICKUP_STATUS.get(
                        jira_issue.fields.status.name.upper())  # For now only update status
                    if jira_status.upper() != existing_clickup_task.status.status.upper():
                        existing_clickup_task.update(status=jira_status)
                        print(f'[INFO] Updating status of {existing_clickup_task.id} to: {jira_status}')
                    existing_issue_in_db['last_update'] = now_datetime.isoformat()
                    self.save_db()
            # If issue does not exist, create a new clickup task
            else:
                new_clickup_id = self.create_clickup_task_from_jira(jira_issue)
                self.db['items'].append({
                    'jira_key': jira_issue_key,
                    'clickup_id': new_clickup_id,
                    'last_update': now_datetime.isoformat()
                })
                print(f'[INFO] Found jira issue - {jira_issue_key}, Created new task in ClickUp - {new_clickup_id}')
                self.save_db()

        # ClickUp
        for clickup_task in self.all_clickup_tasks:
            clickup_task_id = clickup_task.id
            existing_task_in_db = self.search_db(clickup_task_id, 'ClickUp')
            # If the task exist, only check for timestamp, and update jira for any changes
            if existing_task_in_db:
                clickup_last_update = clickup_task.date_updated + timedelta(hours=CLICKUP_TIME_DELTA)
                db_last_update = datetime.fromisoformat(existing_task_in_db['last_update'])
                if clickup_last_update > db_last_update:
                    existing_jira_issue = self.search_task_or_issue(existing_task_in_db['jira_key'])
                    if not existing_jira_issue:
                        print('ERROR! Issue does not exist in all_jira_issues even though in the db')
                        continue
                    # Gets jira and ClickUp status in the Jira standard
                    clickup_status = get_key_by_value(JIRA_TO_CLICKUP_STATUS, clickup_task.status.status.upper())
                    if clickup_status.upper() != existing_jira_issue.fields.status.name.upper():
                        self.jira_client.transition_issue(existing_jira_issue.id, clickup_status)
                        print(f'[INFO] Updating status of {existing_jira_issue.key} to: {clickup_status}')
                    existing_task_in_db['last_update'] = now_datetime.isoformat()
                    self.save_db()
            # If task does not exist, create a new jira task
            else:
                new_jira_key = self.create_jira_issue_from_clickup(clickup_task)
                self.db['items'].append({
                    'jira_key': new_jira_key,
                    'clickup_id': clickup_task_id,
                    'last_update': now_datetime.isoformat()
                })
                print(f'[INFO] Found ClickUp Task - {clickup_task_id}, Created new Issue in Jira - {new_jira_key}')
                self.save_db()


def run_once():
    sync_class = JiraClick()
    sync_class.load_db()
    sync_class.sync()
    sync_class.save_db()


def run_forever(minutes=10):
    while True:
        run_once()
        print(f'Sleeping for {minutes} minutes')
        sleep(60 * minutes)


if __name__ == '__main__':
    print(f'[INFO] JiraClick version {JIRACLICK_VERSION}')
    # For single run - run without parameters, for endless run - run with number of minutes to delay between syncs
    if len(sys.argv) > 1:
        sleep_minutes = int(sys.argv[1])
        run_forever(sleep_minutes)
    run_once()
