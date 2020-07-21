import datetime
import logging
import time

import dataset
from sqlalchemy.types import JSON

from stravaweb import settings

if settings.DEBUG:
    import requests_cache
    requests_cache.install_cache(
        'cache_strava', allowable_codes=(200, 401), allowable_methods=('GET', 'POST'), fast_save=True
    )

import requests
from stravaweb.client import StravaWebClient


def main():
    started_at = time.time()
    logging.basicConfig(level=logging.DEBUG)
    db = dataset.connect(settings.DB_URL)

    cl = StravaWebClient(cookies_filename=settings.COOKIES_PATH, credentials_pool=settings.CREDENTIALS)
    if not cl.is_logged_in():
        print('Login to strava using {}'.format(settings.CREDENTIALS[0][0]))
        cl.login()

    total_new = 0
    for club_id in settings.CLUBS:
        new = load_club_activities(cl, db, club_id)
        total_new += new
    print(
        'Elapsed {:.2f} seconds. New activities: {}. Total activities in DB: {}'.format(
            time.time() - started_at, total_new, db['activities'].count()
        )
    )


def load_club_activities(client, db, club_id):
    current_count = db['activities'].count(club_id=club_id)
    new_activities_saved = 0
    print('Downloading club {} activities ({} in db)'.format(club_id, current_count))
    for i, act in enumerate(client.get_club_activities(club_id)):
        act_string = '[{datetime} {athlete_name} ({athlete_id}) - {title}  ({activity_id})]'.format(**act)
        res = db['activities'].find_one(activity_id=act['activity_id'])
        if res:
            print('- Activity already saved {}'.format(act_string))
            continue
        res = db['access_errors'].find_one(
            id=act['activity_id'], created={'gt': time.time() - datetime.timedelta(days=1).total_seconds()}
        )
        if res:
            print('- Activity is inaccessible {}'.format(act_string))
            continue

        print('Downloading {} {}'.format(i, act_string))
        try:
            data = client.get_activity_data(act['activity_id'])
        except requests.RequestException as err:
            print('Error while downloading', err)
            if err.response.status_code in (401, 404):
                db['access_errors'].insert_ignore({'id': act['activity_id'], 'created': time.time()}, ['id'])
            continue
        if not data.get('latlng'):
            print('No points in data')
            db['access_errors'].insert_ignore({'id': act['activity_id'], 'created': time.time()}, ['id'])
            continue
        print('Loaded, {} points'.format(len(data['latlng'])))
        act.update(data)
        act['club_id'] = club_id
        types = {'latlng': JSON, 'time': JSON, 'velocity_smooth': JSON}
        db['activities'].insert_ignore(act, ['activity_id'], types=types)
        new_activities_saved += 1

    print('New activities for club {}: {}'.format(club_id, new_activities_saved))
    return new_activities_saved


if __name__ == '__main__':
    main()
