# -*- coding: utf-8 -*-

import datetime
import fcntl
import json
import os
import requests
import sys

from imgurpython import ImgurClient
from imgurpython.helpers.error import ImgurClientError,ImgurClientRateLimitError
import RPi.GPIO as GPIO

baseDeployDir = os.path.join('/home', 'pi')
logDir = os.path.join(baseDeployDir, 'log')
youtubeIdsDir = os.path.join(logDir, 'youtube')

# getting an imgur client is slow, so cache it here
_imgurClient = None

_secretsPath = os.path.join(baseDeployDir, 'Chicken', 'config', 'chicken-secrets.json')
with open(_secretsPath) as chickenSecretsJson:
    _secrets = json.load(chickenSecretsJson)

def log(message, imageUrl=None, level='INFO'):
    '''Log a message to a file on disk and Slack.
    imageUrl will be sent to slack() if provided.
    level can be DEBUG, INFO, WARNING, or ERROR.'''
    now = datetime.datetime.now()
    dateStr = now.strftime('%Y-%m-%d %H:%M:%S')
    logFilePath = os.path.join(logDir, 'autodoor.log')
    with open(logFilePath, 'a', 0) as outputFile:
        logLine = '[{}] {} {}\n'.format(dateStr, level, message)
        outputFile.write(logLine)
        if sys.stdin.isatty():
            print logLine, # for interactive usage
    slack(message, imageUrl, level)

def slack(message, imageUrl=None, level=None):
    if level == 'DEBUG':
        channel = '#debug'
    elif level == 'INFO':
        channel = '#general'
    elif level == 'WARNING':
        channel = '#general'
    elif level == 'ERROR':
        channel = '#general'
    else:
        raise Exception('invalid log level')
    payload = {
        'text': message,
        'channel': channel,
    }
    if imageUrl:
        payload['attachments'] = [
            {
                'image_url': imageUrl,
            },
        ]
    url = _secrets['slack']['chickenbotWebhookUrl']
    headers = {'content-type': 'application/json'}
    requests.post(url, data=json.dumps(payload), headers=headers)

_lockPath = os.path.join(logDir, 'gpio.lock')
_lockFd = None

def gpioLock():
    '''Mutex to lock actions against the GPIO. Compatible with Linux
    flock(1).'''
    global _lockFd
    _lockFd = open(_lockPath, 'w')
    fcntl.flock(_lockFd, fcntl.LOCK_EX)

def gpioUnlock():
    '''Unlock GPIO mutex.'''
    global _lockFd
    fcntl.flock(_lockFd, fcntl.LOCK_UN)
    _lockFd.close()

def getLightLevel():
    gpioLock()
    lightLevelExecutable = os.path.join(baseDeployDir, 'bin', 'lightLevel')
    lightLevel = int(os.popen(lightLevelExecutable).read())
    gpioUnlock()
    return lightLevel

_topMagSensor = 31
_bottomMagSensor = 29
def getDoorState():
    '''Get chicken door open/closed state based on magnetic (hall effect)
    sensors or other means. Returns "open", "closed", or "unknown".'''
    gpioLock()
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(_topMagSensor, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(_bottomMagSensor, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    topTripped = (GPIO.input(_topMagSensor) == 0)
    bottomTripped = (GPIO.input(_bottomMagSensor) == 0)
    GPIO.cleanup()
    gpioUnlock()

    if topTripped and bottomTripped:
        doorState = readDoorStateInterleave()
        log('🚦 Both mag sensors tripped! Fallback says "{}".'.format(doorState), level='ERROR')
    elif not topTripped and not bottomTripped:
        doorState = readDoorStateInterleave()
        log('🚦 Neither mag sensor tripped. Fallback says "{}".'.format(doorState), level='DEBUG')
    elif topTripped:
        doorState = 'open'
    elif bottomTripped:
        doorState = 'closed'
    else:
        doorState = 'unknown'

    return doorState

_doorStateInterleaveFile = os.path.join(logDir, 'doorStateInterleave.txt')
def readDoorStateInterleave():
    '''Last-ditch attempt to get door open/closed state based on a file
    written right after the last probably successful (e.g. mag sensor was
    hit) door actuation.'''
    state = open(_doorStateInterleaveFile).read().strip()
    if state != 'open' and state != 'closed':
        state = 'unknown'
    return state

_doorUpDir = 'forward'
_doorDownDir = 'reverse'
def writeDoorStateInterleave(state):
    '''Called after "successful" closing/opening. That is, the mag sensor
    was hit. The trouble is, the motor keeps advancing past the mag sensor
    after shutting down, so we have to record that it "passed" the mag
    sensor.'''
    with open(_doorStateInterleaveFile, 'w') as f:
        f.write('{}\n'.format(state))

def getImgurClient():
    client_id = _secrets['imgur']['client_id']
    client_secret = _secrets['imgur']['client_secret']
    # NOTE since access tokens expire after an hour, only the refresh token is
    # required (library handles autorefresh)
    access_token = None
    refresh_token = _secrets['imgur']['refresh_token']
    mashape_key = _secrets['imgur']['mashape_key']
    return ImgurClient(client_id, client_secret, access_token, refresh_token, mashape_key)

def takePhoto():
    now = datetime.datetime.now()
    fileNameOnly = now.strftime('%Y-%m-%d-%H-%M-%S-auto.jpg')
    photoAbsolutePath = os.path.join(baseDeployDir, 'Pictures', fileNameOnly)
    os.system('raspistill --width 1024 --height 768 --quality 10 --hflip --vflip --output {}'.format(photoAbsolutePath))
    return photoAbsolutePath

def getImgurPostUrl(imgurImageObject):
    return 'https://imgur.com/{}'.format(imgurImageObject['id'])

def getImgurDirectImageLink(imgurImageObject):
    return imgurImageObject['link']

def uploadToImgur(photoAbsolutePath):
    global _imgurClient
    fileNameOnly = os.path.basename(photoAbsolutePath)
    config = { 'album': _secrets['imgur']['album_id'], 'name': fileNameOnly, 'title': fileNameOnly }
    # cache imgur client
    if not _imgurClient: _imgurClient = getImgurClient()
    imgurImageObject = _imgurClient.upload_from_path(photoAbsolutePath, config=config, anon=False)
    return imgurImageObject

_lightLevelDawn = 5
_lightLevelDusk = -15
def doorOracle(lightLevel=None, doorState=None):
    rv = {}

    if not lightLevel: lightLevel = getLightLevel()
    if not doorState: doorState = getDoorState()

    if lightLevel > _lightLevelDawn and doorState != 'open':
        rv['recommend'] = 'open'
        rv['message'] = '🐣 Dawn/daylight detected and door state {}. Opening door.'.format(doorState)
        rv['severity'] = 'DEBUG'
    elif lightLevel < _lightLevelDusk and doorState != 'closed':
        rv['recommend'] = 'close'
        rv['message'] = '🌇 Dusk/nighttime detected and door state {}. Closing door.'.format(doorState)
        rv['severity'] = 'DEBUG'
    else:
        rv['recommend'] = 'none'

    return rv

def systemctl(useSudo=True, action=None, unit=None):
    if useSudo:
        sudo = '/usr/bin/sudo '
    else:
        sudo = ''
    cmd = '{}/bin/systemctl {} {} 2>&1'.format(sudo, action, unit)
    output = os.popen(cmd).read().strip()
    if output:
        log('📡 [{}] had output: [{}]'.format(cmd, output), level='DEBUG')

def postPhoto(photoAbsolutePath):
    try:
        imgurImageObject = uploadToImgur(photoAbsolutePath)
    except (ImgurClientError,ImgurClientRateLimitError) as e:
        log('😓 Imgur upload failed: {}'.format(e), level='DEBUG')
        return None
    imagePage = getImgurPostUrl(imgurImageObject)
    actualImage = getImgurDirectImageLink(imgurImageObject)
    log('📷 Coop photo: {}'.format(imagePage), level='INFO', imageUrl=actualImage)

import chxmotor
_doorUpTimeout = 20
_doorDownTimeout = 13.5
def door(cmd, doorState=None):
    '''Actuate door. cmd can be "open" or "close".'''
    log('🚪 Will {} door now.'.format(cmd), level='DEBUG')
    if not doorState: doorState = getDoorState()
    rv = None
    interleave = None
    if doorState == 'open' and cmd == 'open':
        log('🚧 Door already open.', level='ERROR')
        return False
    elif doorState == 'closed' and cmd == 'close':
        log('🚧 Door already closed.', level='ERROR')
        return False
    elif cmd == 'open':
        gpioLock()
        rv = chxmotor.actuate(_doorUpDir, _topMagSensor, _doorUpTimeout)
        interleave = 'open'
        gpioUnlock()
    elif cmd == 'close':
        gpioLock()
        rv = chxmotor.actuate(_doorDownDir, _bottomMagSensor, _doorDownTimeout)
        interleave = 'closed'
        gpioUnlock()

    if rv:
        if rv['result'] == 'timeout':
            log('⏰ Timed out after {} seconds'.format(rv['elapsed']))
        elif rv['result'] == 'hit_mag_sensor':
            log('🏁 Hit mag sensor after {} seconds'.format(rv['elapsed']), level='DEBUG')
        writeDoorStateInterleave(interleave)

    return True
