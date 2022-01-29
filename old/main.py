import datetime
import sys
import time
from datetime import date, timedelta
from pprint import pprint
from typing import List

import requests
from bs4 import BeautifulSoup
from requests_futures.sessions import FuturesSession
from concurrent.futures import TimeoutError

from mapping import MAPPING

MAIN_URL = 'https://www.onepa.gov.sg/facilities/4810ccmcpa-bm'
PARAMS = {'AspxAutoDetectCookieSupport': 1}

# Form data parameters
DATE = 'content_0$tbDatePicker'  # DD/MM/YYYY
CC = 'content_0$ddlFacilityLocation'  # Refer to mapping.py


class CourtDates:
    ALL_CCS = MAPPING.keys()

    def __init__(self):
        self.__s = FuturesSession()
        self.availability = {}  # internal dict of available dates for cc(s), updated as searches are called

        initial_page = self.__s.get(MAIN_URL)

        # Extract form input data for later submission (required for server-side validation)
        soup = BeautifulSoup(initial_page.result(5).content, 'html.parser')
        form_data = {}
        for item in soup.find_all('input', type='hidden'):
            form_data[item.attrs.get('name')] = item.attrs.get('value')

        form_data['__EVENTTARGET'] = 'content_0$ddlFacilityLocation'

        self.__form_data = form_data

    def __update_availability(self, selected_date, cc_name, result):
        if not self.availability.get(selected_date):
            self.availability[selected_date] = {}

        self.availability.get(selected_date)[cc_name] = result

    def __make_availability_response(self, select_date: datetime.date, cc_name: str):

        form_data_copy = self.__form_data.copy()

        form_data_copy[DATE] = select_date.strftime('%d/%m/%Y')
        form_data_copy[CC] = MAPPING[cc_name]  # Lookup UUID from CC name
        r = self.__s.post(MAIN_URL, params=PARAMS, data=form_data_copy)
        return r

    def __get_availability_from_response(self, response: requests.Response, select_date: datetime.date, cc_name: str):

        result = []

        soup = BeautifulSoup(response.content, 'html.parser')
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
        self.__update_availability(select_date, cc_name, result)
        print(f'Updated availability for {cc_name} on {select_date.strftime("%d/%m/%Y")}')

        return result

    def get_availability_range(self, dates: List[datetime.date], cc_names: List[str], response_timeout: int = 5):
        """
        Given a list of datetime.date(s) and cc_names, updates self.availability and prints result
        :param response_timeout: time to wait for response in s (default 5)
        :param dates: list of dates (datetime.date) to check for
        :param cc_names: list of CC names (note: must be spelt exactly as in mapping.py)
        """

        futures = []

        for select_date in dates:
            for cc_name in cc_names:
                futures.append((self.__make_availability_response(select_date, cc_name), select_date, cc_name))

        for future, select_date, cc_name in futures:
            try:
                self.__get_availability_from_response(future.result(response_timeout), select_date, cc_name)
            except TimeoutError:
                print(f'Response timeout for {select_date}: {cc_name}', file=sys.stderr)

        pprint(self.availability)


# For benchmark purposes
def _test():
    time1 = time.time()
    court_dates = CourtDates()
    dates = [date.today() + timedelta(days=x) for x in range(1)]
    court_dates.get_availability_range(dates, CourtDates.ALL_CCS)
    print(f'Time taken: {time.time() - time1: .2f}')
