from enum import Enum
import re


# State transitions:
# 1 -> 2 -> 3 -> [4, 5, 6]
# 4 -> 1
# 5 -> [4, 6]
# 6 -> [1, 7]
# 7 -> 8
# 8 -> (wait a few seconds, then) 1
class States(Enum):
    waiting = 1
    got_image = 2
    got_image_and_motion = 3
    no_cat_arriving = 4
    not_sure = 5
    cat_arriving = 6
    cat_with_mouse = 7
    cat_flap_locked = 8


class CatDetector(object):

    def __init__(self):
        self._state = States.waiting
        self._snapshot = None
        self._motions = []
        self._images = []
        self._current_event = 0
        self.savefilepattern = re.compile('saved (.*).jpg')
        self.motionpattern = re.compile(
          'motion detected: (\d+) changed pixels (\d+) x (\d+) at (\d+) (\d+)')

    def load_snapshot(self, filename):
        print(f'load snapshot from {filename}')
        basename = filename.split('/')
        parts = basename[-1].split('-')

    def load_image(self, filename):
        print(f'load image from {filename}')
        basename = filename.split('/')
        parts = basename[-1].split('-')
        if self.__state == States.waiting:
            self.__state = Stats.got_image
        else:
            # look at event of previous image to see if should reset
            if int(parts[0]) != self._current_event:
                print('This is a new event, resetting ...')
                self._current_event = parts[0]
                self._motions = []
                self._images = []
            else:
                print(f'Continuing with event {self._current_event}')
        # Append image to self._images

    def motion_detected(self, params):
        (pxcount, width, height, x, y) = params
        print('motion detected')
        if self.__state == States.got_image:
            self.__state = States.got_image_and_motion
        # Append motion to self._motions
        # Evaluate and go to next state
        print('Evaluate image and motion')

    def parse_message(self, message):
        msavefile = re.match(self.savefilepattern, message)
        if msavefile is not None:
            basefilename = msavefile[1].split('/')
            parts = basefilename[-1].split('-')
            if len(parts) < 2:
                return f'Failed to parse save file message {message}'
            elif parts[2] == 'snapshot':
                # This is a message telling us a new snapshot has been taken
                # this.load_snapshot(msavefile[1])
                return 'snapshot'
            else:
                # This is an image from a series
                # this.load_image(msavefile[1])
                return 'image'
        else:
            motion = re.match(self.motionpattern, message)
            if motion is None:
                return f'Failed to recognize message {message}'
            else:
                # this.motion_detected(motion.groups())
                return 'motion'



