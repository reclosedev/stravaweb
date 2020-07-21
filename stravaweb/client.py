import os
import pickle
import logging
import itertools

from lxml import etree

import requests


logger = logging.getLogger(__name__)


class StravaWebClient:

    TOKEN_COOKIE = '_strava4_session'

    def __init__(self, cookies_filename=None, credentials_pool=None):
        self._cookies_filename = cookies_filename
        self.session = requests.session()
        self.url = 'https://www.strava.com/'
        self.session.headers.update({
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'
        })
        if cookies_filename and os.path.exists(cookies_filename):
            self.load_cookies()
        if credentials_pool is None:
            credentials_pool = []
        self._credentials_pool = itertools.cycle(credentials_pool)
        self._n_credentials = len(credentials_pool)
        if credentials_pool:
            next(self._credentials_pool)

    def load_cookies(self, filename=None):
        filename = filename or self._cookies_filename
        assert filename
        with open(filename, 'rb') as fp:
            cookies = pickle.load(fp)
            self.session.cookies.update(cookies)

    def save_cookies(self, filename=None):
        filename = filename or self._cookies_filename
        assert filename
        with open(filename, 'wb') as fp:
            pickle.dump(self.session.cookies, fp)

    def login(self, email=None, password=None):
        self.session.cookies.clear()
        if not email or not password:
            email, password = next(self._credentials_pool)
        params = self._get_login_params()
        params.update({
            'email': email, 'password': password,
        })
        self._html_request('post', 'session', data=params)
        if self._cookies_filename:
            self.save_cookies()

    def get_activity_data(self, activity_id):
        data = self._api_request(
            'get',
            'activities/{}/streams?stream_types%5B%5D=latlng&stream_types%5B%5D=time&stream_types%5B%5D=velocity_smooth'.format(activity_id)
        )
        return data

    def get_mentionable_ahtletes(self):
        resp = self._html_request('get', 'athlete/mentionable_athletes')
        if 'login' in resp.url:
            raise requests.RequestException()
        if 'consents' in resp.url:  # https://www.strava.com/athlete/consents/welcome
            return self._process_consents()
        return resp.json()

    def _process_consents(self, text=None, referrer=None):  # TODO it doesn't work. Error 500
        logger.info('Processing contests')
        if not text:
            resp = self._html_request('get', 'athlete/consents/terms_of_service')
            referrer = resp.url
            text = resp.text
        doc = etree.HTML(text)
        inputs = doc.xpath('//form/input')
        if not inputs:
            logger.debug('No more consents')
            return text
        params = {}
        for inp in inputs:
            params[inp.attrib['name']] = inp.attrib['value']
        print(params)
        params['consent'] = 'approved'
        try:
            resp = self._html_request(
                'post', 'athlete/consents', data=params,
                headers={'referer': referrer}
            )
        except requests.RequestException as exc:
            logger.error('Error %s:', exc)
            raise
        self._process_consents(resp.text, resp.url)

    def is_logged_in(self):
        try:
            self.get_mentionable_ahtletes()
        except requests.RequestException:
            return False
        return True

    def _get_login_params(self):
        text = self._html_request('get', 'login').content
        doc = etree.HTML(text)
        token = doc.xpath('//form[@id="login_form"]/input[@name="authenticity_token"]')[0].attrib['value']
        return {'utf8': '✓', 'authenticity_token': token}

    def get_club_activities(self, club_id):
        params = {}
        while True:
            logger.debug('Querying with params %s', params)
            resp = self._html_request('get', 'clubs/{}/feed?feed_type=club'.format(club_id), params=params)
            try:
                chunk = list(self._parse_feed_page(resp.text))
            except Exception as exc:
                logger.error('Error %s. Response text:\n%s', exc, resp.text)
                raise
            if not chunk:
                break
            yield from chunk
            ts = chunk[-1]['updated_at']
            params.update({'before': int(ts), 'cursor': ts})

    def _parse_feed_page(self, text):
        doc = etree.HTML(text)
        activities = doc.cssselect('div.activity,div.group-activity')
        for act in activities:
            data_rank = act.attrib.get('data-rank')
            if not data_rank:
                continue

            act_time = act.xpath('.//time/@datetime')[0]
            if 'group-activity' in act.attrib['class']:
                for sub_act in act.cssselect('div ul.list-entries li.entity-details'):
                    link = sub_act.cssselect('h4 strong a.minimal')[0]
                    activity_id = int(link.attrib['href'].rsplit('/', 1)[-1])
                    athlete = sub_act.cssselect('a.entry-athlete')[0]
                    athlete_id = int(athlete.attrib['href'].rsplit('/', 1)[-1])
                    entry = {
                        'updated_at': float(data_rank),
                        'title': link.text,
                        'activity_id': activity_id,
                        'datetime': act_time,
                        'athlete_name': athlete.text.strip(),
                        'athlete_id': athlete_id,
                    }
                    yield entry
            else:
                link = act.xpath('.//h3/strong/a')[0]
                activity_id = int(link.attrib['href'].rsplit('/', 1)[-1])
                athlete = act.cssselect('a.entry-athlete')[0]
                athlete_id = int(athlete.attrib['href'].rsplit('/', 1)[-1])
                entry = {
                    'updated_at': float(data_rank),
                    'title': link.text,
                    'activity_id': activity_id,
                    'datetime': act_time,
                    'athlete_name': athlete.text.strip(),
                    'athlete_id': athlete_id,
                }
                yield entry

    def _api_request(self, method, path, json=True, *args, **kwargs):
        resp = None
        for i in range(self._n_credentials or 1):
            resp = self.session.request(method, self.url + path, *args, **kwargs)
            if resp.status_code == 429:
                pair = next(self._credentials_pool, None)
                if pair is None:
                    resp.raise_for_status()
                logger.debug('Got to many requests for path. Trying next credentials %s', pair[0])
                self.login(*pair)
            else:
                break

        resp.raise_for_status()
        if json:
            try:
                return resp.json()
            except Exception:
                logger.error('JSON decode error for\n%s', resp.text)
                raise
        return resp

    def _html_request(self, method, path, *args, **kwargs):
        return self._api_request(method, path, json=False, *args, **kwargs)
