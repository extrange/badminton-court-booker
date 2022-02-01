import json
from typing import TypedDict, List, Dict
from datetime import datetime, date, timezone, timedelta
import time
import random
from pyppeteer import launch
import asyncio
import nest_asyncio
from dotenv import dotenv_values
nest_asyncio.apply()

# Note: myactivesg.com requires login before court details will be shown


def get_dates(
) -> List[datetime]:
    """
    Returns the datetimes of all specified days of the week 14 days from current date

    Args: None

    Returns:
        A list of datetimes
    """
    date_list = [(today+timedelta(days=n)) for n in range(16)]
    if days_of_week == 'All':
        return date_list
    else:
        days_of_week_list = [d.strip().title()
                             for d in days_of_week.split(",")]
        filtered_date_list = [
            d for d in date_list if d.strftime("%a") in days_of_week_list]
        return filtered_date_list


async def get_venues(
) -> List[str]:
    """
    Searches all venues with badminton courts and returns a list of venues

    Args: None

    Returns:
        A list of venues
    """
    utc_date = round(today.replace(tzinfo=timezone.utc).timestamp())
    url = search_url.format(activity_id, '296', utc_date)
    browser = await launch()
    page = await browser.newPage()
    await page.goto(url)
    venues = await page.evaluate('''() => [...document.querySelectorAll('#facVenueSelection option')]
                   .map((element) => {
                    let venue = {}
                    venue['name'] = element.text
                    venue['value'] = element.value
                    return venue
                    })
            ''')
    await browser.close()
    return venues


async def get_slots(
) -> Dict[str, Dict[str, Dict[str, int]]]:
    """
    Searches venues with badminton courts, and
    returns a dictionary of {venue: [available slots]}.

    Args: None

    Returns:
        A dictionary of {venue: {date: [available_timeslots]}}
        E.g.
        {
            'Bukit Gombak Sports Hall': {
                '29-01-2022': {
                    '13:00:00-14:00:00': 2,
                    '16:00:00-17:00:00': 1
                }
            }
        }
    """

    browser = await launch()
    page = await browser.newPage()
    await page.goto(login_url, {
        'waitUntil': 'load',
        'timeout': 0
    })
    await page.type('[ id = email ]', username)
    await page.type('[ id = password ]', password)
    await page.click('[id = btn-submit-login]')

    slots = {}
    for venue in venue_list:
        venue_id = venue['value']
        venue_name = venue['name']
        slots[venue_name] = {}
        for date in date_list:
            date_str = date.strftime("%d-%m-%Y")
            utc_date = round(date.replace(tzinfo=timezone.utc).timestamp())
            url = search_url.format(activity_id, venue_id, utc_date)

            time.sleep(random.randrange(3))
            newTab = await browser.newPage()
            await newTab.goto(url, {
                'waitUtil': 'domcontentloaded',
                'timeout': 0
            })
            await newTab.waitForSelector('.timeslot-container')
            timeslots_list = await newTab.evaluate('''() => [...document.querySelectorAll('.timeslot-container input[name="timeslots[]"]')]
                .map((element) => {
                    let slot = element.value.split(';')[3] + '-' + element.value.split(';')[4]
                    return slot
                    })
            ''')
            timeslots = {i: timeslots_list.count(i) for i in timeslots_list}
            # remove timeslots that are out of range
            # super slow
            for k in list(timeslots.keys()):
                start_time = int(k[:2])
                if start_time < earliest_timeslot or start_time > latest_timeslot:
                    del timeslots[k]
            # add to dictionary if timeslots is not empty
            if timeslots:
                slots[venue_name][date_str] = timeslots
            await newTab.close()
    await page.close()
    return slots

if __name__ == '__main__':
    config = dotenv_values('.env')
    username = config['USERNAME']
    password = config['PASSWORD']

    login_url = "https://members.myactivesg.com/auth"
    search_url = "https://members.myactivesg.com/facilities/view/activity/{}/venue/{}?time_from={}"

    activity_id = 18  # badminton
    earliest_timeslot = 13  # 24hr format
    latest_timeslot = 17  # 24hr format
    days_of_week = "Wed,Sat"  # or All

    today = datetime.combine(date.today(), datetime.min.time())
    print("Extracting dates:")
    date_list = get_dates()
    print(date_list)
    print("Extracting venues")
    venue_list = [{'name': 'Clementi Sports Hall', 'value': '296'},  {
        'name': 'Bukit Gombak Sports Hall', 'value': '293'}]
    # venue_list = (asyncio.get_event_loop().run_until_complete(
    #     get_venues()))
    # TimeoutError: Waiting for selector ".timeslot-container" failed: timeout 30000ms exceeds
    print(venue_list)
    print("Extracting slots")
    slots = (asyncio.get_event_loop().run_until_complete(
        get_slots()))

    print(json.dumps(slots, sort_keys=False, indent=4))
