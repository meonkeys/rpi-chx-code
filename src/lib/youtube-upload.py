#!/usr/bin/python -ttu
# -*- coding: utf-8 -*-

# Derivative work of
# https://github.com/youtube/api-samples/blob/master/python/upload_video.py .
# from commit 60b1bca333abb7aad04618a38c313426d3e0d5c6
# available under Apache 2.0 license.
# See also: https://developers.google.com/youtube/v3/guides/uploading_a_video

import datetime
import httplib
import httplib2
import os
import random
import sys
import time

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

import chxlib

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
  httplib.IncompleteRead, httplib.ImproperConnectionState,
  httplib.CannotSendRequest, httplib.CannotSendHeader,
  httplib.ResponseNotReady, httplib.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret. You can acquire an OAuth 2.0 client ID and client secret from
# the {{ Google Cloud Console }} at
# {{ https://cloud.google.com/console }}.
# Please ensure that you have enabled the YouTube Data API for your project.
# For more information about using OAuth2 to access the YouTube Data API, see:
#   https://developers.google.com/youtube/v3/guides/authentication
# For more information about the client_secrets.json file format, see:
#   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
CLIENT_SECRETS_FILE = "/home/pi/Chicken/lib/client_secrets.json"

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is
# missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the {{ Cloud Console }}
{{ https://cloud.google.com/console }}

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def get_authenticated_service(args):
  flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE,
    scope=YOUTUBE_UPLOAD_SCOPE,
    message=MISSING_CLIENT_SECRETS_MESSAGE)

  storage = Storage("%s-oauth2.json" % sys.argv[0])
  credentials = storage.get()

  if credentials is None or credentials.invalid:
    credentials = run_flow(flow, storage, args)

  return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
    http=credentials.authorize(httplib2.Http()))

def initialize_upload(youtube, options):
  tags = None
  if options.keywords:
    tags = options.keywords.split(",")

  body=dict(
    snippet=dict(
      title=options.title,
      description=options.description,
      tags=tags,
      categoryId=options.category
    ),
    status=dict(
      privacyStatus=options.privacyStatus
    )
  )

  # Call the API's videos.insert method to create and upload the video.
  insert_request = youtube.videos().insert(
    part=",".join(body.keys()),
    body=body,
    # The chunksize parameter specifies the size of each chunk of data, in
    # bytes, that will be uploaded at a time. Set a higher value for
    # reliable connections as fewer chunks lead to faster uploads. Set a lower
    # value for better recovery on less reliable connections.
    #
    # Setting "chunksize" equal to -1 in the code below means that the entire
    # file will be uploaded in a single HTTP request. (If the upload fails,
    # it will still be retried where it left off.) This is usually a best
    # practice, but if you're using Python older than 2.6 or if you're
    # running on App Engine, you should set the chunksize to something like
    # 1024 * 1024 (1 megabyte).
    media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
  )

  resumable_upload(insert_request, options)

def saveId(youtubeVideoId):
    '''Write a file using the (just-uploaded?) YouTube video id. Later, another
    process will do something with these.'''
    filename = os.path.join(chxlib.youtubeIdsDir, youtubeVideoId)
    fileHandle = open(filename, 'w')
    fileHandle.close()

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request, options):
  response = None
  error = None
  retry = 0
  basename = os.path.basename(options.file)
  while response is None:
    try:
      status, response = insert_request.next_chunk()
      if response is not None:
        if 'id' in response:
          saveId(response['id'])
          chxlib.log('📹 Coop motion detected and video captured. Uploading to YouTube, id {}. Local file {}'.format(response['id'], basename), level='DEBUG')
        else:
          chxlib.log('👎 The upload failed with an unexpected response: {}'.format(response), level='DEBUG')
          exit(1)
    except HttpError, e:
      if e.resp.status in RETRIABLE_STATUS_CODES:
        error = "🙅 A retriable HTTP error %d occurred uploading %s:\n%s" % (e.resp.status, basename, e.content)
      else:
        raise
    except RETRIABLE_EXCEPTIONS, e:
      error = "🙅 A retriable error occurred uploading %s: %s" % (basenam, e)

    if error is not None:
      chxlib.log(error, level='DEBUG')
      retry += 1
      if retry > MAX_RETRIES:
        chxlib.log('❌ No longer attempting to retry {}.'.format(basename), level='DEBUG')
        exit(1)

      max_sleep = 2 ** retry
      sleep_seconds = random.random() * max_sleep
      chxlib.log("😴 Sleeping %f seconds and then retrying %s..." % (sleep_seconds, basename), level='DEBUG')
      time.sleep(sleep_seconds)

def getDefaultVideoTitle():
    now = datetime.datetime.now()
    return now.strftime('ChickenCam %Y-%m-%d %H:%M:%S')

if __name__ == '__main__':
  argparser.add_argument("--file", required=True, help="Video file to upload")
  argparser.add_argument("--title", help="Video title", default=getDefaultVideoTitle())
  argparser.add_argument("--description", help="Video description",
    default='Captured by a motion-triggered ChickenCam powered by GNU/Linux Free Software running on a Raspberry Pi.')
  argparser.add_argument("--category", default="22",
    help="Numeric video category. " +
      "See https://developers.google.com/youtube/v3/docs/videoCategories/list")
  argparser.add_argument("--keywords", help="Video keywords, comma separated",
    default="")
  argparser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES,
    default=VALID_PRIVACY_STATUSES[2], help="Video privacy status.")
  args = argparser.parse_args()

  if not os.path.exists(args.file):
    chxlib.log('☝ Please specify a valid file using the --file= parameter.', level='ERROR')
    exit(1)

  youtube = get_authenticated_service(args)
  try:
    initialize_upload(youtube, args)
  except HttpError, e:
    basename = os.path.basename(args.file)
    chxlib.log("💔 An HTTP error %d occurred uploading %s:\n%s" % (e.resp.status, basename, e.content), level='DEBUG')
