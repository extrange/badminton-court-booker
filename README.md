# Onepa.gov.sg Badminton Court Availability Checker

Scrapes the onepa.gov.sg website for available badminton courts.

Done purely over http requests (no web browser automation/emulation), so it's much faster.

Built using requests_future.Sessions and BeautifulSoup

Usage:
```python
from main import CourtDates
from datetime import date

dates = [date(2020, 11, 20), date(2020, 11, 21)]
cc_names = ['Bukit Batok CC', 'Gek Poh Ville CC']

court_dates = CourtDates()
court_dates.get_availability_range(dates, cc_names)
# court_dates.get_availability_range(dates, CourtDates.ALL_CCS)  # Search all CCs for given dates
# court_dates.get_availability(date(2020,11,21), 'Bukit Batok CC')  # Single date and CC search

print(court_dates.availability)
```

Output:
```
{
 datetime.date(2020, 11, 20): {'Bukit Batok CC': [],
                               'Gek Poh Ville CC': [],},
 datetime.date(2020, 11, 21): {'Bukit Batok CC': [],
                               'Gek Poh Ville CC': [('10:30 AM - 11:30 AM',
                                                  'normal')]},
```

You can find the mapping from names to UUIDS in `mapping.py`. Use `CourtDates.ALL_CCS` to iterate through all CCs.

The `availability` property of `CourtDates` is updated on each call of `get_availability_range`.

To enter a range of dates use 
```python
from datetime import date, timedelta

dates = [date(2020, 11, 20) + timedelta(days=x) for x in range(5)]
```