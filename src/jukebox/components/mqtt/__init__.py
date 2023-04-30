import paho.mqtt.client as mqtt
import jukebox
import jukebox.plugs as plugin
import jukebox.multitimer as multitimer
from jukebox.publishing.subscriber import Subscriber
import components.volume
import components.hostif.linux
import components.player
import components.playermpd
import components.rfid.reader
import json
import logging
import time


topic_name = 'phoniebox-future3'
logger = logging.getLogger('jb.mqtt')

client = mqtt.Client("phoniebox-future3")
client.username_pw_set(
    username="mqtt", password="P4a$$w0rd"
)


def _publish_attr(topic, payload=''):
    logger.debug(f'Send attribute {topic}: {payload}')
    client.publish(topic_name+'/attribute/'+topic, payload)


def _get_current_time_milli():
    return int(round(time.time() * 1000))


attributes = dict()


def _send_throttled(topic, payload):
    global attributes
    now = _get_current_time_milli()

    if topic in attributes:
        prev = attributes[topic]
        time_since_last_update = now - prev['last_update']
        if prev['value'] == payload and time_since_last_update < 30000:
            return
        if prev['value'] != payload and time_since_last_update < 1000:
            return

    attributes[topic] = {
        'value': payload,
        'last_update': now
    }
    _publish_attr(topic, payload)


def send_volume_update(volume, is_min, is_max):
    _send_throttled('volume', volume)


def send_card_swipe(card_id: str, state: int):
    _send_throttled('card_id', card_id)
    _send_throttled('card_is_registered', state)


def send_playerstatus(mpd_status):
    _send_throttled('state', mpd_status['state'])
    if mpd_status['title'] is not None:
        _send_throttled('title', mpd_status['title'])
        _send_throttled('artist', mpd_status['artist'])
        _send_throttled('album', mpd_status['album'])
        _send_throttled('track', mpd_status['track'])
        _send_throttled('duration', mpd_status['duration'])
        _send_throttled('repeat', mpd_status['repeat'])
        _send_throttled('random', mpd_status['random'])
        _send_throttled('single', mpd_status['single'])

        if mpd_status.get('elapsed') is not None:
            _send_throttled('elapsed', mpd_status['elapsed'])
        else:
            _send_throttled('elapsed', '0.0')


def publish_system_stats():
    ip = components.hostif.linux.get_ip_address()
    [ip4, ip6] = ip.split(' ')
    _publish_attr('ip4', ip4)
    _publish_attr('ip6', ip6)

    auto_hotspot_state = components.hostif.linux.get_autohotspot_status()
    _publish_attr('auto_hotspot', auto_hotspot_state)

    pi_throttled = components.hostif.linux.get_throttled()
    _publish_attr('pi_throttled', pi_throttled)

    cpu_temp = components.hostif.linux.get_cpu_temperature()
    _publish_attr('cpu_temp', cpu_temp)

    version = jukebox.version()
    _publish_attr('version', version)


def not_name_found_yet():
    publish_system_stats()
    playlistinfo = components.playermpd.player_ctrl.list_albums()
    logger.debug(f"playlistinfo- {playlistinfo}")


status_thread = None
status_thread = multitimer.GenericEndlessTimerClass(
        'mqtt.status', 30, not_name_found_yet)

def on_connect(client, userdata, flags, rc):
    global status_thread
    logger.debug(f"Connected with result code {rc}")
    client.publish(topic_name+"/state", 'online')
    
    components.volume.pulse_control.on_volume_change_callbacks.register(
        send_volume_update)
    
    components.player.on_player_status_change_callback.register(
        send_playerstatus)
    
    components.rfid.reader.rfid_card_detect_callbacks.register(send_card_swipe)
    
    not_name_found_yet()

    status_thread.start()


def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))


client.on_connect = on_connect
client.on_message = on_message


@plugin.initialize
def start_client():
    client.connect("192.168.xxx.xxx", 1883, 60)
    client.loop_start()


@plugin.atexit
def stop_client(**ignored_kwargs):
    global status_thread
    status_thread.cancel()
    client.publish(topic_name+"/state", 'offline')
    client.loop_stop()
    client.disconnect()
