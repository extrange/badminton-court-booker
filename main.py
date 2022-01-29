import datetime
from typing import TypedDict
from dotenv import dotenv_values

USERNAME = dotenv_values('.env')['USERNAME']
PASSWORD = dotenv_values('.env')['PASSWORD']

# Note: myactivesg.com requires login before court details will be shown


def get_courts(
    start_date: datetime.date, end_date: datetime.date
) -> dict(str, dict(datetime.date, list(str))):
    """
    Searches all facilities with badminton courts, and
    returns a dictionary of {facility: [available courts]}.

    Args:
        start_date: Starting date to begin search (inclusive)
        end_date: End date of search (inclusive)

    Returns:
        A dictionary of {facility: {date: [available_timeslots]}}
        E.g.
        {
            'Bukit Gombak CC': {
                datetime.date(2022, 1, 29): [
                    '1pm-2pm', '2pm-3pm'
                ]
            }
        }
    """
    pass
