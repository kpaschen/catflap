import cv2
from datetime import date, datetime
from enum import Enum
import numpy as np
import re
from trainer import Trainer


# Two state machines.
class MessageStates(Enum):
    waiting = 1
    got_motion = 2
    got_image = 3
    got_image_and_motion = 4


class CatStates(Enum):
    waiting = 1
    no_cat_arriving = 2
    not_sure = 3
    cat_arriving = 4
    cat_with_prey = 5


class CatDetector(object):
    statModel = None

    @classmethod
    def setupCatDetector(cls, modelfile, trainingfile):
        if trainingfile is not None:
          # Cannot load a model? Train our own!
          trainer = Trainer()
          with open(trainingfile, 'r') as tfile:
            trainer.addTrainingDataFromFile(tfile)
          trainer.trainClassifier()
          cls.statModel = trainer.knn_model
        else: 
          # What kind of model are we loading? Could have a factory
          # here but for now, just basics.
          suffix = modelfile.split('.')[-1]
          if suffix == 'knn':
            cls.statModel = cv2.ml.KNearest_load(modelfile)
          else:
            raise NotImplementedError('Only supporting knn models right now')

    @classmethod
    def makeCatDetector(cls):
        if cls.statModel:
            return cls(cls.statModel)
        return None

    def __init__(self, statModel):
        self._message_state = MessageStates.waiting
        self._cat_state = CatStates.waiting
        self._snapshot = None
        self._motions = []
        self._images = []
        self._trajectory = []
        self._current_event = -1
        self.savefilepattern = re.compile('saved (.*.jpg)')
        self.motionpattern = re.compile(
          'motion detected: (\d+) changed pixels (\d+) x (\d+) at (\d+) (\d+)')
        self._statModel = statModel
        self.base_resolution = (240.0, 320.0)


    # TODO: all the file reading operations should probably be done
    # asynchronously and in their own thread pool (so as not to block
    # the main event loop). However, since the images are pretty small
    # (about 16K) and we get at most two per second, it's not a huge
    # concern.
    # There is also literally nothing else I want the system to do while
    # it's loading and processing an image, so maybe threads are not the
    # way to go here anyway :-).
    def load_snapshot(self, filename):
        img = cv2.imread(filename)
        if img is not None:
            self._snapshot = cv2.imread(filename)
            return 'snapshot'
        else:
            return 'Failed to load snapshot from {0}'.format(filename)

    def determine_trajectory(self, t1=None, t2=None):
        if t1 is None and t2 is None:
            if len(self._trajectory) < 2:
                return None
            t1 = self._trajectory[-1]
            t2 = self._trajectory[-2]
        xdiff = np.sign(t1[0] - t2[0])
        ydiff = np.sign(t1[1] - t2[1])
        return { -1 : { 0: 'w', -1: 'nw', 1: 'sw' },
                  0 : { 0: 'c', -1: 'n',  1: 's' },
                  1 : { 0: 'e', -1: 'ne', 1: 'se' } }[xdiff][ydiff]
            

    def decide_if_cat_has_prey(self, image, trajectory):
        return False

    def reset(self):
        self._current_event = -1
        self._motions = []
        self._images = []
        self._trajectory = []
        self._message_state = MessageStates.waiting
        self._cat_state = CatStates.waiting

    def process_image_and_motion(self):
        self._message_state = MessageStates.waiting
        if self._cat_state == CatStates.no_cat_arriving:
            # TODO: might want to wait a bit longer before deciding
            # not to do anything.
            return 'ignoring image as no cat arriving'
        elif self._cat_state == CatStates.cat_with_prey:
            return 'ignoring image as cat flap already locked'
        if not len(self._images):
            return 'cannot process image as there are none in the list'
        img = self._images[-1]
        motion = self._motions[-1]
        if self._cat_state != CatStates.cat_arriving:
            detected = self.evaluate_motion_and_image(motion=motion, image=img)
            if detected == 0:
                self._cat_state = CatStates.no_cat_arriving
            elif detected == 1:
                self._cat_state = CatStates.not_sure
            elif detected == 2:
                self._cat_state = CatStates.no_cat_arriving
            elif detected == 3:
                self._cat_state = CatStates.cat_arriving
        if self._cat_state == CatStates.cat_arriving:
            has_prey = self.decide_if_cat_has_prey(image=img, trajectory=self._trajectory)
            if has_prey:
                # TODO: lock cat flap and set a timer to unlock it
                return 'event {0} image {1}: should lock cat flap '.format(
                        self._current_event, len(self._images))
        return 'event {0} image {1} evaluated as {2}'.format(
                self._current_event, len(self._images), self._cat_state)


    def load_image(self, filename):
        # TODO: maybe don't do this until we know we need it.
        img = cv2.imread(filename)
        if img is None:
            return 'Failed to load image from {0}'.format(filename)
        basename = filename.split('/')
        parts = basename[-1].split('-')
        if self._message_state == MessageStates.waiting:
            self._message_state = MessageStates.got_image
        elif self._message_state == MessageStates.got_motion:
            self._message_state = MessageStates.got_image_and_motion
        if int(parts[0]) != self._current_event:
            # reset() will be called by the daemon if too much time
            # has passed since the last event.
            # If reset() hasn't been called, it's possible this is a new
            # event following quickly after another event. Sometimes the
            # cats sit about in front of the cat flap for a while.
            self._current_event = int(parts[0])
            self._cat_state = CatStates.waiting
        self._images.append(img)
        if self._message_state == MessageStates.got_image_and_motion:
            return self.process_image_and_motion()
        else:
            return 'got image but no motion event'

    def evaluate_motion_and_image(self, motion, image):
        if motion is None:
            return self.evaluate_image(image)
        (pxcount, width, height, x, y) = motion
        left = round(x - width/2)
        right = round(x + width/2)
        top = round(height - y)
        bottom = round(height + y)
        print('motion translated to raw coordinates: %s %s %s %s' % (left, right, top, bottom))
        if image is not None:
            imgwidth, imgheight, _ = image.shape
            print('image has width %d and height %d' % (imgwidth, imgheight))
            width_factor = self.base_resolution[0] / imgwidth
            height_factor = self.base_resolution[1] / imgheight
            print('width factor %f height %f' % (width_factor, height_factor))
            left = left * width_factor
            right = right * width_factor
            top = height * height_factor
            bottom = bottom * height_factor
        print('motion coordinates normalised: %s %s %s %s' % (left, right, top, bottom))
        features = np.ndarray((1, 4), dtype=np.float32,
                buffer=np.array((left, right, top, bottom), dtype=np.float32))
        retval, _ = self._statModel.predict(features)
        return int(retval)

    def get_coords(self, image):
        cur = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        ret, cur = cv2.threshold(cur, 127, 255, cv2.THRESH_BINARY)
        cur = cv2.Canny(cur, 100, 200, 3)
        lines = cv2.HoughLinesP(cur, 1, np.pi/180, 40, 25, 35)
        if lines is None or not len(lines):
            print('no lines found on image')
            return None
        imgwidth, imgheight, _ = image.shape
        width_factor = self.base_resolution[0] / imgwidth
        height_factor = self.base_resolution[1] / imgheight
        left = np.float64(imgwidth)
        right = np.float64(0.0)
        top = np.float64(imgheight)
        bottom = np.float64(0.0)
        for points in lines:
            p = points[0]
            left = min(left, p[0], p[2])
            right = max(right, p[0], p[2])
            top = min(top, p[1], p[3])
            bottom = max(bottom, p[1], p[3])
        left = left * width_factor
        right = right * width_factor
        top = top * height_factor
        bottom = bottom * height_factor
        print('returning %f %f %f %f' % (left, right, top, bottom))
        for x in (left, right, top, bottom):
            print(type(x))
        return (left, right, top, bottom)

    def evaluate_image(self, image):
        coords = self.get_coords(image)
        if coords is None:
            return 0  # no cat?
        (left, right, top, bottom) = coords
        features = np.ndarray((1, 4), dtype=np.float32,
                buffer=np.array((left, right, top, bottom), dtype=np.float32))
        print('image coordinates normalised: %s %s %s %s' % (left, right, top, bottom))
        retval, _ = self._statModel.predict(features)
        print('i think this is %s' % Trainer.string_for_label(retval))
        return int(retval)

    def motion_detected(self, params):
        # TODO: make use of these. should be more helpful than the canny-based
        # detection. Motion events appear to be sent just before an image saved
        # event, most of the time.
        # (pxcount, width, height, x, y) = params
        self._motions.append(params)
        self._trajectory.append((params[3], params[4]))
        if self._message_state == MessageStates.got_image:
            # may want to check timestamps as well?
            self._message_state = MessageStates.got_image_and_motion
            return self.process_image_and_motion()
        else:
            self._message_state = MessageStates.got_motion
            return 'motion: {0}'.format(params)

    def parse_message(self, message):
        msavefile = re.match(self.savefilepattern, message)
        if msavefile is not None:
            basefilename = msavefile.groups()[0].split('/')
            parts = basefilename[-1].split('-')
            if len(parts) < 3:
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
                return self.motion_detected(tuple(int(m) for m in motion.groups()))



