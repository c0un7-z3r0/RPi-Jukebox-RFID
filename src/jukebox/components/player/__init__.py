import os
import re
import logging
import jukebox.cfghandler
from jukebox.callingback import CallbackHandler
from typing import (List, Optional, Callable)

logger = logging.getLogger('jb.player')
cfg = jukebox.cfghandler.get_handler('jukebox')


def _get_music_library_path(conf_file):
    """Parse the music directory from the mpd.conf file"""
    pattern = re.compile(r'^\s*music_directory\s*"(.*)"', re.I)
    directory = None
    with open(conf_file, 'r') as f:
        for line in f:
            res = pattern.match(line)
            if res:
                directory = res.group(1)
                break
        else:
            logger.error(f"Could not find music library path in {conf_file}")
    logger.debug(f"MPD music lib path = {directory}; from {conf_file}")
    return directory


class MusicLibPath:
    """Extract the music directory from the mpd.conf file"""
    def __init__(self):
        self._music_library_path = None
        mpd_conf_file = cfg.setndefault('playermpd', 'mpd_conf', value='~/.config/mpd/mpd.conf')
        try:
            self._music_library_path = _get_music_library_path(os.path.expanduser(mpd_conf_file))
        except Exception as e:
            logger.error(f"Could not determine music library directory from '{mpd_conf_file}'")
            logger.error(f"Reason: {e.__class__.__name__}: {e}")

    @property
    def music_library_path(self):
        return self._music_library_path


# ---------------------------------------------------------------------------


_MUSIC_LIBRARY_PATH: Optional[MusicLibPath] = None


def get_music_library_path():
    """Get the music library path"""
    global _MUSIC_LIBRARY_PATH
    if _MUSIC_LIBRARY_PATH is None:
        _MUSIC_LIBRARY_PATH = MusicLibPath()
    return _MUSIC_LIBRARY_PATH.music_library_path

class PlayerStatusCallbackHandler(CallbackHandler):
    """
    Callbacks are executed when
        * new player status is published
    """

    def register(self, func: Callable[[int, bool, bool], None]):
        """
        Add a new callback function :attr:`func`.

        Callback signature is

        .. py:function:: func(volume: int, is_min: bool, is_max: bool)
            :noindex:

            :param volume: Volume level
            :param is_min: 1, if volume level is minimum, else 0
            :param is_max: 1, if volume level is maximum, else 0
        """
        super().register(func)

    def run_callbacks(self, sink_name, alias, sink_index, error_state):
        """:meta private:"""
        super().run_callbacks(sink_name, alias, sink_index, error_state)


on_player_status_change_callback = PlayerStatusCallbackHandler('on_player_status_change_callback', logger)
