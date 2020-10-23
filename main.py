import requests
from bs4 import BeautifulSoup
import datetime

from typing import List

from mapping import MAPPING
from pprint import pprint
from concurrent.futures import ThreadPoolExecutor

MAIN_URL = 'https://www.onepa.gov.sg/facilities/4810ccmcpa-bm'
PARAMS = {'AspxAutoDetectCookieSupport': 1}

# Form data parameters
DATE = 'content_0$tbDatePicker'  # DD/MM/YYYY
CC = 'content_0$ddlFacilityLocation'  # Refer to mapping.py


class CourtDates:

    ALL_CCS = MAPPING.keys()

    def __init__(self):
        self.s = requests.session()
        self.availability = {}  # internal dict of available dates for cc(s), updated as searches are called

        initial_page = self.s.get(MAIN_URL)

        # Extract form input data
        soup = BeautifulSoup(initial_page.content, 'html.parser')
        form_data = {}
        for item in soup.find_all('input', type='hidden'):
            form_data[item.attrs.get('name')] = item.attrs.get('value')

        form_data['__EVENTTARGET'] = 'content_0$ddlFacilityLocation'

        self.form_data = form_data

    def _update_availability(self, date, cc_name, result):
        if not self.availability.get(date):
            self.availability[date] = {}

        self.availability.get(date)[cc_name] = result

    def get_availability(self, date: datetime.date, cc_name: str):

        form_data_copy = self.form_data.copy()

        form_data_copy[DATE] = date.strftime('%d/%m/%Y')
        form_data_copy[CC] = MAPPING[cc_name]  # Lookup UUID from CC name

        result = []

        r = self.s.post(MAIN_URL, params=PARAMS, data=form_data_copy)
        soup = BeautifulSoup(r.content, 'html.parser')
        timeslots = [x.text for x in soup.find('div', class_='timeslotsContainer').find_all('div', class_='slots')]

        court_list = []
        for court in soup.find_all('div', class_='facilitiesType'):
            court_list.append([x.attrs.get('class')[1] for x in court.find_all('span', class_='slots')])

        availability_list = list(map(lambda *args: 'normal' if ('normal' in args or 'peak' in args) else 'booked',
                                     *court_list))

        for timeslot, availability in zip(timeslots, availability_list):
            if availability == 'normal' or availability == 'peak':
                result.append((timeslot, availability))

        # Update internal availability table
        self._update_availability(date, cc_name, result)
        print(f'Updated availability for {cc_name} on {date.strftime("%d/%m/%Y")}')

        return result

    def get_availability_range(self, dates: List[datetime.date], cc_names: List[str]):

        executor = ThreadPoolExecutor(5)

        for date in dates:
            for cc_name in cc_names:
                executor.submit(self.get_availability, date, cc_name)

        executor.shutdown()
        pprint(self.availability)