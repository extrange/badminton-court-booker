
import time
import json
import random
import os
from dotenv import dotenv_values
from typing import List, Dict
import datetime
from datetime import date, timezone, timedelta
from pyppeteer import launch
import asyncio
import requests
from bs4 import BeautifulSoup

config = dotenv_values('.env')
data_file = 'data.json'

# Search inputs
activity_id = 18  # badminton
days_of_week = "Thu"  # or All

# Search links
login_url = "https://members.myactivesg.com/auth"
search_url = "https://members.myactivesg.com/facilities/view/activity/{}/venue/{}?time_from={}"

# login information
# Note: myactivesg.com requires login before court details will be shown
username = config['USERNAME']
password = config['PASSWORD']


def get_dates(
) -> List[datetime.datetime]:
    """
    Returns the datetimes of all specified days of the week 14 days from current date

    Args: None

    Returns:
        A list of datetimes
    """
    print("Extracting dates...")
    date_list = [(today+timedelta(days=n)) for n in range(16)]
    if days_of_week == 'All':
        return date_list
    else:
        days_of_week_list = [d.strip().title()
                             for d in days_of_week.split(",")]
        filtered_date_list = [
            d for d in date_list if d.strftime("%a") in days_of_week_list]
        return filtered_date_list


def get_venues(
) -> Dict[str, List[str]]:
    """
    Searches all venues with badminton courts and returns a dictionary of venues

    Args: None

    Returns:
        A dictionary of venues lists - schools which are available only on weekends and others which are available on weekdays and weekend e.g. Sports Halls
        E.g.
        {
            'schools': [...], 
            'others' : [...]
        }
    """
    print("Extracting venues...")
    venues = {}
    utc_date = round(today.replace(tzinfo=timezone.utc).timestamp())
    url = search_url.format(activity_id, '296', utc_date)
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    facVenueSelection = soup.find('select', {'id': 'facVenueSelection'})
    option_list = facVenueSelection.find_all('option')
    school_list = []
    oth_list = []
    for option in option_list:
        venue = {'name': option.text, 'value': option.get('value')}
        if any(x in option.text for x in ['School', 'College']):
            school_list.append(venue)
        elif "Select" not in option.text:
            oth_list.append(venue)
    venues['schools'] = school_list
    venues['others'] = oth_list
    return venues


async def get_login_cookies(
) -> Dict[str, str]:
    print("Retrieving cookies...")
    browser = await launch()
    page = await browser.newPage()
    await page.goto(login_url, {
        'waitUntil': 'load',
        'timeout': 0
    })
    await page.type('[ id = email ]', username)
    await page.type('[ id = password ]', password)
    await page.click('[id = btn-submit-login]')
    r = await page._client.send('Network.getAllCookies')

    cookies_list = r.get('cookies', {})
    cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies_list}
    await page.close()
    return cookies_dict


def make_request(url, cookies_dict, n, consec_timeout):
    nil_str = "* There are no available slots for your preferred date."
    r = requests.get(url, cookies=cookies_dict)
    print(r.status_code)
    soup = BeautifulSoup(r.text, 'html.parser')
    timeslot_container = soup.find(class_='timeslot-container')
    if nil_str in timeslot_container.text:
        consec_timeout = consec_timeout + 1
        print("Login timeout at item {}".format(n))
        sleep_time = random.randint(10, 20)
        if consec_timeout > 1:
            sleep_time = random.randint(200, 300)
            if consec_timeout > 3:
                sleep_time = random.randint(8000, 10000)
        print("{} Consecutive timeout: sleeping for {} seconds".format(
            consec_timeout, sleep_time))
        time.sleep(sleep_time)
        cookies_dict = (asyncio.get_event_loop().run_until_complete(
            get_login_cookies()))
        make_request(url, cookies_dict, n, consec_timeout)
    else:
        return timeslot_container


def get_slots(
) -> Dict[str, Dict[str, Dict[str, int]]]:
    """
    Searches venues with badminton courts, and
    returns a dictionary of {venue: [available slots]}.

    Args: None

    Returns:
        A dictionary of {date: {venue: [available_timeslots]}}
        E.g.
        {
            '29-01-2022': {
                'Bukit Gombak Sports Hall': {
                    '13:00:00': 2,
                    '16:00:00': 1
                }
            }
        }
    """
    print("Extracting slots...")
    cookies_dict = (asyncio.get_event_loop().run_until_complete(
        get_login_cookies()))

    timeslots = {}
    n = 0
    for date in date_list:
        date_str = date.strftime("%d-%m-%Y")
        utc_date = round(date.replace(tzinfo=timezone.utc).timestamp())
        print(date_str)
        timeslots[date_str] = {}
        venue_list = venues['schools'] + \
            venues['others'] if date.weekday() > 4 else venues['others']
        for venue in venue_list:
            venue_id = venue['value']
            venue_name = venue['name']
            url = search_url.format(activity_id, venue_id, utc_date)
            n = n + 1
            timeslot_container = make_request(
                url, cookies_dict, n, 0)
            avail_list = timeslot_container.find_all(
                'input', {"name": "timeslots[]"})
            timeslot_list = [v.get('value').split(';')[-2]
                             for v in avail_list]
            timeslot_dict = {i: timeslot_list.count(
                i) for i in timeslot_list}
            # add to dictionary if timeslots is not empty
            if timeslot_dict:
                timeslots[date_str][venue_name] = timeslot_dict
    return timeslots


today = datetime.datetime.combine(date.today(), datetime.time.min)
today_str = today.strftime("%d-%m-%Y")
date_list = get_dates()
# print(date_list)
venues = get_venues()
# print(venues)
start_time = time.time()
timeslots = get_slots()
print("--- %s seconds ---" % (time.time() - start_time))
print(timeslots)
if os.path.exists(data_file):
    with open('data.json') as fp:
        data = json.load(fp)
else:
    data = {}
data[today_str] = timeslots
with open('data.json', 'w') as fp:
    json.dump(data, fp)
print("Data saved.")
