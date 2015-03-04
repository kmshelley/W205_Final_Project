# ==============================================================================
# TITLE           : strava_data_acquisition.py
# DESCRIPTION     : W205 - Storage and Retrieving Data - Project
#                   Acquiring and Storing Data from Strava
# AUTHOR          : Rajesh Thallam
# DATE            : 2/16/2015
# VERSION         : 0.1
# USAGE           : python strava_data_acquisition.py
# NOTES           : Script can be executed from python console
# PY_VERSION      : Python 2.7.9 (final)
# ==============================================================================
import os
import datetime
import time
import json
import urllib
import urllib2
import StringIO

import requests

from W205_Final_Project.strava.acquire import config


def main():
    bounds = get_address_coordinates(config.zipcode)
    segment_ids = get_segments(bounds)
    get_segment_efforts(segment_ids)


def get_segments(bounds):
    p('INFO', 'Fetching segments for bounds ')
    params = {"bounds":
              str(bounds['sw.lat']) + "," + str(bounds['sw.lng']) + "," + str(bounds['ne.lat']) + "," +
              str(bounds['ne.lng'])}
    print params
    req = requests.get(config.STRAVA_API_SEGMENT_EXPLORE_URI, headers=config.STRAVA_API_HEADER, params=params)
    print req.json()

    segments = req.json()

    i = 0
    segment_ids = []
    while i < len(segments['segments']):
        segment_ids.append(segments['segments'][i]['id'])
        i += 1

    return segment_ids

def get_segment_efforts(segment_ids):
    for segment_id in segment_ids:
        filename = 'strava_segment_efforts.%d' % segment_id
        file_out = open(filename, "w")

        segment_efforts = []
        req = requests.get(config.STRAVA_API_SEGMENT_URI % segment_id, headers=config.STRAVA_API_HEADER)
        nb_efforts = req.json()['effort_count']

        p('INFO', 'Fetching ' + str(nb_efforts) + ' effort summaries for segment ' + str(segment_id))

        for i in range(1, 2 + nb_efforts / config.STRAVA_PAGE_LIMIT):
            p('INFO', 'Making summary request ' + str(i))
            req = requests.get(
                config.STRAVA_API_SEGMENT_ALL_EFFORTS_URI % segment_id,
                headers=config.STRAVA_API_HEADER,
                params={'per_page': config.STRAVA_PAGE_LIMIT, 'page': i})

            if req.status_code != 200:
                p("ERR ", "Received error " + str(req.status_code) + " for summary request " + str(i))
            else:
                print >> file_out, json.dumps(req.json())
                segment_efforts.extend(req.json())

            time.sleep(2)


def p(category, message):
    print \
        "[", os.path.basename(__file__), "]", \
        "[", datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S"), "]", \
        "[", category, "]", \
        message


def get_address_coordinates(address):
        print address
        urlparams = {
            'address': address[0],
            'sensor': 'false',
        }
        url = 'http://maps.google.com/maps/api/geocode/json?' + urllib.urlencode(urlparams)
        print url
        response = urllib2.urlopen(url)
        responsebody = response.read()

        body = StringIO.StringIO(responsebody)
        print body
        result = json.load(body)

        if 'status' not in result or result['status'] != 'OK':
            return None
        else:
            return {
                'sw.lat': result['results'][0]['geometry']['bounds']['southwest']['lat'],
                'sw.lng': result['results'][0]['geometry']['bounds']['southwest']['lng'],
                'ne.lat': result['results'][0]['geometry']['bounds']['northeast']['lat'],
                'ne.lng': result['results'][0]['geometry']['bounds']['northeast']['lng']
            }


if __name__ == "__main__":
    main()