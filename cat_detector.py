import cv2
from datetime import date, datetime
from enum import Enum
import numpy as np
import re
from trainer import Trainer


# State transitions:
# 1 -> 2 -> [3, 4, 5]
# Always: return to state 1 when new event starts
# 4 -> [3, 4, 5]
# 5 -> [3, 5, 6] (3: cat definitely not carrying mouse)
# 6 -> 7  (6 and 7 are not really separate states)
class States(Enum):
    waiting = 1
    got_image = 2
    no_cat_arriving = 3
    not_sure = 4
    cat_arriving = 5
    cat_with_mouse = 6
    cat_flap_locked = 7


class CatDetector(object):

    def __init__(self, modelfile, trainingfile):
        self._state = States.waiting
        self._snapshot = None
        self._motions = []
        self._images = []
        self._current_event = -1
        self.savefilepattern = re.compile('saved (.*.jpg)')
        self.motionpattern = re.compile(
          'motion detected: (\d+) changed pixels (\d+) x (\d+) at (\d+) (\d+)')

        self._statModel = None
        if trainingfile is not None:
          # Cannot load a model? Train our own!
          trainer = Trainer()
          with open(trainingfile, 'r') as tfile:
            trainer.addTrainingDataFromFile(tfile)
          trainer.trainClassifier()
          self._statModel = trainer.knn_model
        else: 
          # What kind of model are we loading? Could have a factory
          # here but for now, just basics.
          suffix = modelfile.split('.')[-1]
          if suffix == 'knn':
              self._statModel = cv2.ml.KNearest_load(modelfile)
          else:
              raise NotImplementedError('Only supporting knn models right now')


    # TODO: all the file reading operations should probably be done
    # asynchronously and in their own thread pool (so as not to block
    # the main event loop). However, since the images are pretty small
    # (about 16K) and we get at most two per second, it's not a huge
    # concern.
    def load_snapshot(self, filename):
        img = cv2.imread(filename)
        if img is not None:
            self._snapshot = cv2.imread(filename)
            return 'snapshot'
        else:
            return 'failed to load snapshot from {0}'.format(filename)

    def decide_if_cat_has_prey(self, img):
        return False

    def reset(self):
        self._current_event = -1
        self._motions = []
        self._images = []
        self._state = States.waiting

    def load_image(self, filename):
        img = cv2.imread(filename)
        if img is None:
            return 'Failed to load image from {0}'.format(filename)
        basename = filename.split('/')
        parts = basename[-1].split('-')
        if self._state == States.waiting:
            self._state = States.got_image
        if int(parts[0]) != self._current_event:
            # New event, reset.
            self.reset()
            self._current_event = int(parts[0])
            self._state = States.got_image
        self._images.append(img)
        if self._state == States.no_cat_arriving:
            # TODO: might want to wait a bit longer before deciding
            # not to do anything.
            return 'ignoring image as no cat arriving'
        elif self._state == States.cat_flap_locked:
            return 'ignoring image as cat flap already locked'
        # TODO: if self._state == States.cat_arriving:
        #  different evaluation as have to decide whether cat has mouse
        #  start by subtracting snapshot from current image
        # Evaluate and go to next state
        if self._state != States.cat_arriving:
            detected = self.evaluate_image(img)
            if detected == 0:
                self._state = States.no_cat_arriving
            elif detected == 1:
                self._state = States.not_sure
            elif detected == 2:
                self._state = States.no_cat_arriving
            elif detected == 3:
                self._state = States.cat_arriving
        if self._state == States.cat_arriving:
            has_prey = self.decide_if_cat_has_prey(img)
            if has_prey:
                # TODO: lock cat flap and set a timer to unlock it
                return 'event {0} image {1}: should lock cat flap '.format(
                        self._current_event, len(self._images))
        return 'event {0} image {1} evaluated as {2}'.format(
                self._current_event, len(self._images), self._state)

    def evaluate_image(self, img):
        cur = cv2.cvtColor(self._images[-1], cv2.COLOR_BGR2GRAY)
        ret, cur = cv2.threshold(cur, 127, 255, cv2.THRESH_BINARY)
        cur = cv2.Canny(cur, 100, 200, 3)
        lines = cv2.HoughLinesP(cur, 1, np.pi/180, 40, 25, 35)
        if lines is None or not len(lines):
            return None
        left = 400
        right = 0
        top = 240
        bottom = 0
        for points in lines:
            p = points[0]
            left = min(left, p[0], p[2])
            right = max(right, p[0], p[2])
            top = min(top, p[1], p[3])
            bottom = max(bottom, p[1], p[3])
        features = np.ndarray((1, 4), dtype=np.float32, buffer=np.array((left, right, top, bottom), dtype=np.float32))
        retval, _ = self._statModel.predict(features)
        return int(retval)

    def motion_detected(self, params):
        # TODO: make use of these. should be more helpful than the canny-based
        # detection. Motion events appear to be sent just before an image saved
        # event, most of the time.
        (pxcount, width, height, x, y) = params
        return 'motion: {0}'.format(params)

    def parse_message(self, message):
        msavefile = re.match(self.savefilepattern, message)
        if msavefile is not None:
            basefilename = msavefile.groups()[0].split('/')
            parts = basefilename[-1].split('-')
            if len(parts) < 2:
                return 'Failed to parse save file message {0}'.format(message)
            elif parts[2] == 'snapshot.jpg':
                # This is a message telling us a new snapshot has been taken
                return self.load_snapshot(msavefile.groups()[0])
            else:
                # This is an image from a series
                return self.load_image(msavefile.groups()[0])
        else:
            motion = re.match(self.motionpattern, message)
            if motion is None:
                return 'Failed to recognize message {0}'.format(message)
            else:
                return self.motion_detected(motion.groups())



