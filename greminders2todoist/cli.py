# -*- coding: utf-8 -*-

"""Console script for greminders2todoist."""
import sys
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from lxml.etree import _Element, _ElementTree
from todoist import TodoistAPI

import click
from lxml import etree
import csv

from typing import List, NamedTuple, Optional, Iterator, Tuple, Union, Dict, TypeVar, Callable, cast, Set

from collections import namedtuple
from dataclasses import dataclass

from typing_extensions import Literal

from re import match

from pprint import pprint

Frequency = Literal['daily','weekly','monthly','yearly']

State = Literal['active','upcoming','archived']

Weekday = Literal['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

Month = Literal[
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
]

def month_num(month: Month) -> int:
    return ['January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',].index(month) + 1

# JSON = Union[Dict[str, "JSON"], List["JSON"], str, int, float, bool, None]


T = TypeVar('T')
U = TypeVar('U')


def maybe(x: Optional[T], f: Callable[[T], U]) -> Optional[U]:
    return f(x) if x is not None else None


def ensure(x: Optional[T]) -> T:
    if x is None:
        raise Exception()
    else:
        return x


class Recurrence(NamedTuple):
    # Monthly means either day_of_month or day_of_week.
    frequency: Frequency
    start: datetime
    end: datetime
    every: int
    hour: int
    # If monthly, then which day of the month (e.g. the 21st)?
    day_of_month: Optional[int]
    # If monthly or weekly, then which weekday?
    # Note: in the UI it's (now?) possible to specify multiple
    # weekdays when weekly, but not worrying about that for this dataset.
    day_of_week: Optional[Weekday]
    # If yearly, then which month?
    month: Month
    # If monthly, and day_of_week is Saturday, then which Saturday? (1 for first, -1 for last, etc.)
    weekday_num: Optional[int]


class Task(NamedTuple):
    title: str
    created: datetime
    state: State
    due: Optional[datetime]
    recurrence: Optional[Recurrence]


def node_to_dict(task_node: _Element) -> Dict[str, Union[str, Dict[str, str]]]:
    def gen():
        for field_node in task_node.findall('ul/li'):
            [key, value] = [child.text for child in field_node]
            subfields = (node_to_dict(field_node[1]))
            if len(subfields) > 0:
                value = subfields
            yield key.rstrip(':'), value
    return dict(gen())


def chop(xs: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    return {k: v for k,v in xs.items() if len(v) < 30}


def scan_fields(tree: _ElementTree) -> List[Dict[str, Set[str]]]:
    task_fields: Dict[str, Set[str]] = {}
    location_fields: Dict[str, Set[str]] = {}
    recurrence_fields: Dict[str, Set[str]] = {}
    for task_node in tree.findall('/body/ul/li'):
        task_dict = dict(node_to_dict(task_node))
        for key, val in task_dict.items():
            if key not in ['Recurrence info', 'Location']:
                task_fields.setdefault(key, set()).add(cast(str, val))
        if task_dict.get('Location'):
            location_dict = cast(Dict[str, str], task_dict['Location'])
            for key, val in location_dict.items():
                location_fields.setdefault(key, set()).add(val)
        if task_dict.get('Recurrence info'):
            recurrence_dict = cast(Dict[str, str], task_dict['Recurrence info'])
            for key, val in recurrence_dict.items():
                recurrence_fields.setdefault(key, set()).add(val)
    task_fields = chop(task_fields)
    location_fields = chop(location_fields)
    recurrence_fields = chop(recurrence_fields)

    return [task_fields, recurrence_fields, location_fields]


def nth(x: int) -> str:
    return '1st' if x == 1 else '2nd' if x == 2 else '3rd' if x == 3 else '{}th'.format(x)


def proc_date(task: Task) -> Optional[str]:
    rec = task.recurrence
    if rec:
        result = ''
        hour = '{}am'.format(rec.hour) if rec.hour <= 12 else '{}pm'.format(rec.hour - 12)
        if rec.frequency == 'monthly':
            assert rec.day_of_week or rec.day_of_month
            if rec.day_of_week:
                assert rec.every == 1
                result = "every {} {} at {}".format(
                    'last' if rec.weekday_num == -1 else nth(rec.weekday_num),
                    rec.day_of_week,
                    hour
                )
            elif rec.day_of_month:
                result = 'every {} {} at {} starting on the {}'.format(
                    rec.every,
                    'month',
                    hour,
                    nth(rec.day_of_month)
                )
        elif rec.frequency == 'weekly':
            assert rec.every == 1
            if rec.every == 1:
                result = 'every {} at {}'.format(rec.day_of_week, hour)
            else:
                # This is interpreted as "3rd Wednesday" rather than "3 Wednesdays"
                assert False
                result = 'every {} {}s at {}'.format(
                    rec.every,
                    rec.day_of_week,
                    hour
                )
        elif rec.frequency == 'yearly':
            assert rec.every == 1
            result = 'every {}/{} at {}'.format(month_num(rec.month), rec.day_of_month, hour)
        elif rec.frequency == 'daily':
            result = 'every {} days at {}'.format(
                rec.every,
                hour
            )
        else:
            assert False
        return result
    elif task.due:
        return str(task.due).rsplit(':',1)[0]
    else:
        return None


SCOPES = [
    'data:read_write'
]



class MyInstalledAppFlow(InstalledAppFlow):
    # Todoist expects client_id and client_secret to be included in body
    def fetch_token(self, **kwargs):
        super().fetch_token(include_client_id=True, **kwargs)

    # Todoist does not have expiry on tokens
    @property
    def credentials(self):
        session = self.oauth2session
        client_config = {}

        if not session.token:
            raise ValueError(
                'There is no access token for this session, did you call '
                'fetch_token?')

        credentials = Credentials(
            session.token['access_token'],
            refresh_token=session.token.get('refresh_token'),
            id_token=session.token.get('id_token'),
            token_uri=client_config.get('token_uri'),
            client_id=client_config.get('client_id'),
            client_secret=client_config.get('client_secret'),
            scopes=session.scope)

        return credentials


@click.command()
def main(args=None):
    """Console script for greminders2todoist."""

    flow = MyInstalledAppFlow.from_client_secrets_file('client.json', SCOPES)
    creds: Credentials = flow.run_local_server(port=3423)
    api = TodoistAPI(creds.token)
    api.sync()

    tree: _ElementTree = etree.parse(open('./Reminders.html'), etree.HTMLParser())
    pprint(scan_fields(tree))
    rows = [
        dict(
            type='task',
            content=task.title,
            priority=4,
            indent=None,
            author=None,
            responsible=None,
            date=proc_date(task),
            date_lang='en',
            timezone=None
        )
        for task in gen_tasks(tree)
        if task.state != 'archived' and
           (task.recurrence or task.due and task.due > datetime.now())
    ]
    with open('out.csv', 'w') as outfile:
        writer = csv.DictWriter(
            outfile,
            ['type', 'content', 'priority', 'indent', 'author', 'responsible', 'date', 'date_lang', 'timezone']
        )
        writer.writeheader()
        writer.writerows(rows)

    [inbox] = [p for p in api.state['projects'] if p['name'] == 'Inbox']
    for task in rows:
        api.items.add(task['content'], inbox['id'], date_string=task['date'])
    api.commit()
    return 0


# TODO: Weekday number, Every


def gen_tasks(tree: _ElementTree) -> Iterator[Task]:
    for task_node in tree.findall('/body/ul/li'):
        task_dict = dict(node_to_dict(task_node))
        recurrence = None
        if task_dict.get('Recurrence info'):
            assert isinstance(task_dict, dict)
            recnode = cast(Dict[str, str], task_dict['Recurrence info'])
            recurrence = Recurrence(
                frequency=cast(Frequency, recnode['Frequency']),
                start=ensure(parse_timestamp_ms(recnode['Start'])),
                end=ensure(parse_timestamp_ms(recnode['End'])),
                hour=int(recnode['Hour of day to fire']),
                every=maybe(recnode.get('Every'), int) or 1,
                weekday_num=maybe(recnode.get('Weekday number'), int),
                day_of_month=maybe(recnode.get('Day number of month'), parse_day_num),
                day_of_week=maybe(recnode.get('Day of week'), lambda x: cast(Weekday, x)),
                month=maybe(recnode.get('Month of year'), lambda x: cast(Month, x)),
            )
        simple_fields = cast(Dict[str, str], task_dict)
        task = Task(
            title=simple_fields['Title'],
            created=ensure(parse_timestamp_ms(simple_fields['Created time'])),
            state=cast(State, simple_fields['State']),
            due=maybe(simple_fields.get('Due date'), lambda x: parse_timestamp_ms(x)),
            recurrence=recurrence
        )
        print(task)
        yield task


def parse_day_num(x: str) -> Optional[int]:
    return None if x == '[]' else \
      int(ensure(match(r'^\[(\d+)\]$', x)).groups()[0])


def parse_timestamp_ms(timestamp_ms: str) -> Optional[datetime]:
    if timestamp_ms == 'unspecified':
        return None
    return datetime.fromtimestamp(int(float(timestamp_ms) / 1000))


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
