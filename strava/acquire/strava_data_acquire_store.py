import config
import os
import sys
import requests
import datetime
import time
import json
import urllib
import urllib2
import StringIO
import pprint
import pymongo
from pymongo import MongoClient
from ..util import log

logger = log.getLogger(__name__)

# MongoDB Client & DB
client = MongoClient('mongodb://localhost:27017/')
db = client['strava']

PARAMS = {"bounds": "37.695010" + "," + "-122.510605" + "," + "37.815531" + "," + "-122.406578"}


def explore_segments():
    logger.info('Exploring segments for bounds: {0}'.format(PARAMS))
    res = requests.get(config.STRAVA_API_SEGMENT_EXPLORE_URI, headers=config.STRAVA_API_HEADER, params=PARAMS)

    #print pprint.pprint(res.json())
    segments = res.json()
    for segment in segments['segments']:
        yield segment


def fetch_store_segment_and_leaderboards():
    segments_collection = db['segments']
    leaderboard_collection = db['leaderboards']

    for segment in explore_segments():
        segment_id = segment["id"]
        logger.info('Fetching segment: {0}'.format(segment_id))
        res = requests.get(config.STRAVA_API_SEGMENT_URI % segment_id, headers=config.STRAVA_API_HEADER)

        _id = None
        try:
            #Insert Segment into MongoDB
            _id = segments_collection.insert(res.json())
        except pymongo.errors.DuplicateKeyError as dk:
            logger.info("### Exception inserting segment: %s", dk)
            #Get Segment ID from DB
            _id = segments_collection.find_one({'id': segment_id})["_id"]
            # This segment has already been processed earlier
            #continue

        logger.info("DB Unique Key %s", _id)

        num_athletes = res.json()['athlete_count']
        logger.info('Athlete Count: {0}'.format(num_athletes))

        page_num = 1
        entry_num = 0;

        while page_num < 2 + num_athletes / config.STRAVA_PAGE_LIMIT:
            leaderboard_batch = []
            logger.info("[Segment:{0}] Fetching Leader-board Page: {1}".format(segment_id, page_num))


            res = requests.get(config.STRAVA_API_SEGMENT_LEADERBOARD_URI % segment_id,
                               headers=config.STRAVA_API_HEADER,
                               params={'per_page': config.STRAVA_PAGE_LIMIT, 'page': page_num})
            '''
            res = requests.get(config.STRAVA_API_SEGMENT_ALL_EFFORTS_URI % segment_id,
                               headers=config.STRAVA_API_HEADER)
            '''

            #pprint.pprint(res.json())

            try:
                if res.status_code != 200 or "errors" in res.json():
                    pprint.pprint(res.json())
                    logger.info("Sleeping after Requesting Retry for Page: ", page_num)
                    time.sleep(60)
                    continue
            except Exception as e:
                logger.info(res)
                logger.info("### Exception: ", e)
                logger.info("Sleeping after Exception for Page: %s", page_num)
                time.sleep(60*5)
                continue

            page_num += 1

            for entry in res.json()['entries']:
                #pprint.pprint(entry)
                entry_num += 1
                entry["_segment_id"] = _id
                leaderboard_batch.append(entry)

            try:
                #Insert Efforts Batch into MongoDB
                ids = leaderboard_collection.insert(leaderboard_batch)
                #print(ids)
                logger.info("[Segment:%s][Total:%d] Total Number of Leaderboard entries inserted into Mongo is %d",
                                            segment_id, num_athletes, entry_num)
            except pymongo.errors.DuplicateKeyError as dk:
                logger.info("### Exception inserting leaderboard: %s", dk)




