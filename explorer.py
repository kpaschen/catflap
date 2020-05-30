import cv2
import numpy as np

class imageExplorer:
    def onCannyTrackbar(self, x):
        # The trackbar always starts at 0, but 3 is the lowest legal value for aperture.
        if x <= 3:
            x = 3
        self.cannyAperture = x

    def onHoughDistTrackbar(self, x):
        self.houghDistResolution = x

    def onHoughAngleTrackbar(self, x):
        # actual resolution will be (x * np.pi)/180
        self.houghAngleResolution = x

    def onHoughMinLLTrackbar(self, x):
        self.houghMinLL = x

    def onHoughMaxLGTrackbar(self, x):
        self.houghMaxLG = x

    def onHoughStrengthTrackbar(self, x):
        self.houghStrength = x

    def onContourMinSize(self, x):
        self.contourMinSize = x

    def onCannyMin(self, x):
        self.cannyMin = x

    def onCannyMax(self, x):
        self.cannyMax = x

    def __init__(self, filename, cat_detector, labelfile):
        self.windowName = 'Processed image'
        self.cannyAperture = 3
        self.cannyMin = 100
        self.cannyMax = 200
        self.houghMinLL = 25
        self.houghMaxLG = 35
        self.houghStrength = 40
        self.houghDistanceResolution = 1
        self.houghAngleResolution = 1
        self.contourMinSize = 30
        self.filename = filename
        self.coords = None
        self.labelfile = labelfile
        self.cat_detector = cat_detector
        self.cascades = {}
        self.cascade_colours = {}
        # All training data is relative to this resolution.
        self.base_resolution = (240.0, 320.0)
        for cascade_name in [
                'frontalface_default',
                'frontalcatface_extended',
                'profileface',
                'eye'
                ]:
            c = cv2.CascadeClassifier()
            if c.load(cv2.samples.findFile(cv2.data.haarcascades + 'haarcascade_' + cascade_name + '.xml')):
                self.cascades[cascade_name] = c
                self.cascade_colours[cascade_name] = (255, 0, 0)
            else:
                print('failed to load cascade for %s' % cascade_name)
        c = cv2.CascadeClassifier()
        if c.load(cv2.samples.findFile('./cascades/cat-arriving/cascade.xml')):
            self.cascades['localcats'] = c
            self.cascade_colours['localcats'] = (0, 255, 0)
        else:
            print('failed to load local cascade from ./cascades/cat-arriving/cascade.xml')
        c2 = cv2.CascadeClassifier()
        if c2.load(cv2.samples.findFile('./cascades/cat-head-full/cascade.xml')):
            self.cascades['catfaces'] = c2
            self.cascade_colours['catfaces'] = (0, 0, 255)
        else:
            print('failed to load local cascade from ./cascades/cat-head-full/cascade.xml')
        c3 = cv2.CascadeClassifier()
        if c3.load(cv2.samples.findFile('./cascades/cat-head-focus/cascade.xml')):
            self.cascades['catfaces-focus'] = c3
            self.cascade_colours['catfaces-focus'] = (0, 0, 0)
        else:
            print('failed to load local cascade from ./cascades/cat-head-focus/cascade.xml')
        cv2.namedWindow(self.windowName)
        cv2.createTrackbar('Canny aperture size', self.windowName, self.cannyAperture, 9, self.onCannyTrackbar)
        cv2.createTrackbar('Canny min', self.windowName, self.cannyMin, 200, self.onCannyMin)
        cv2.createTrackbar('Canny max', self.windowName, self.cannyMax, 400, self.onCannyMax)
        cv2.createTrackbar('Hough min line length', self.windowName, self.houghMinLL, 100, self.onHoughMinLLTrackbar)
        cv2.createTrackbar('Hough max line gap', self.windowName, self.houghMaxLG, 100, self.onHoughMaxLGTrackbar)
        cv2.createTrackbar('Hough strength', self.windowName, self.houghStrength, 200, self.onHoughStrengthTrackbar)
        cv2.createTrackbar('Hough distance', self.windowName, self.houghDistanceResolution, 10, self.onHoughDistTrackbar)
        cv2.createTrackbar('Hough angle', self.windowName, self.houghAngleResolution, 90, self.onHoughDistTrackbar)
        cv2.createTrackbar('Contour min size', self.windowName, self.contourMinSize, 2000, self.onContourMinSize)

    def shift_coords(self, coords, direction):
        fudge = 10
        if direction == 'n':
            return (coords[0], coords[1], coords[2] - fudge, coords[3])
        if direction == 's':
            return (coords[0], coords[1], coords[2], coords[3] + fudge)
        if direction == 'w':
            return (coords[0] - fudge, coords[1], coords[2], coords[3])
        if direction == 'e':
            return (coords[0], coords[1] + fudge, coords[2], coords[3])
        if direction == 'ne':
            x = self.shift_coords(coords, 'n')
            return self.shift_coords(x, 'e')
        if direction == 'nw':
            x = self.shift_coords(coords, 'n')
            return self.shift_coords(x, 'w')
        if direction =='se':
            x = self.shift_coords(coords, 's')
            return self.shift_coords(x, 'e')
        if direction =='sw':
            x = self.shift_coords(coords, 's')
            return self.shift_coords(x, 'w')
        return coords

    def drawLinesOnImg(self, lines, img):
        w, h, _ = img.shape
        left = w
        right = 0
        top = h
        bottom = 0
        for points in lines:
            print(points[0])
            p = points[0]
            left = min(left, p[0], p[2])
            right = max(right, p[0], p[2])
            top = min(top, p[1], p[3])
            bottom = max(bottom, p[1], p[3])
            cv2.line(img, (p[0],p[1]), (p[2],p[3]), (0, 0, 255), 1)
        self.coords = (left, right, top, bottom)
        print('left %d, right %d, top %d, bottom %d' % (left, right, top, bottom))
        
    def exploreImage(self, img, snap=None, motion=None, previous_motion=None):
        self.cur = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if snap is not None:
            self.snap = cv2.cvtColor(snap, cv2.COLOR_BGR2GRAY)
        else:
            self.snap = None
        trajectory = None
        if self.cat_detector is not None and previous_motion is not None:
            trajectory = self.cat_detector.determine_trajectory((motion[3], motion[4]),
                    (previous_motion[3], previous_motion[4]))
            print('trajectory: %s' % trajectory)
        self.motion = motion
        cv2.imshow(self.windowName, self.cur)
        print('shell: q to quit, b motion box, c canny, h find lines with hough, t threshold, '
              'o contours, s subtract snapshot, x extract roi, + zoom in, '
              '- zoom out, r reset')

        while(1):
          pressed = cv2.waitKey(0)
          print(pressed)
          if pressed == 113: # 'q' for quit
              break
          elif pressed == 43: # + for zoom in
              self.cur = cv2.resize(self.cur, None, fx=1.2, fy=1.2, interpolation=cv2.INTER_CUBIC) 
              cv2.imshow(self.windowName, self.cur)
          elif pressed == 45: # - for zoom out
              self.cur = cv2.resize(self.cur, None, fx=0.8, fy=0.8, interpolation=cv2.INTER_CUBIC) 
              cv2.imshow(self.windowName, self.cur)
          elif pressed == 98: # 'b' for motion box
              if self.motion is None:
                  print('no motion, no box')
              else:
                  left = self.motion[3] - self.motion[1]/2
                  right = self.motion[3] + self.motion[1]/2
                  top = self.motion[4] - self.motion[2]/2
                  bottom = self.motion[4] + self.motion[2]/2
                  self.coords = (left, right, top, bottom)
                  topleft = (int(left), int(top))
                  bottomright = (int(right), int(bottom))
                  self.colour = cv2.cvtColor(self.cur, cv2.COLOR_GRAY2BGR)
                  cv2.rectangle(self.colour, topleft, bottomright, (0, 0, 255), 1)
                  cv2.imshow(self.windowName, self.colour)
          elif pressed == 99: # 'c' for canny
            self.cur = cv2.Canny(self.cur, self.cannyMin, self.cannyMax, self.cannyAperture)
            cv2.imshow(self.windowName, self.cur)
          elif pressed == 101: # 'e' equalizeHist
            self.cur = cv2.equalizeHist(self.cur)
            cv2.imshow(self.windowName, self.cur)
          elif pressed == 102: # 'f' for classification with haar
              # recommend equalizeHist before running this
              self.colour = cv2.cvtColor(self.cur, cv2.COLOR_GRAY2BGR)
              for name, cascade in self.cascades.items():
                  c = cascade.detectMultiScale(self.cur, minNeighbors=20)
                  print('cascade %s detected %s' % (name, c))
                  if len(c):
                      colour = self.cascade_colours[name]
                      for (x,y,w,h) in c:
                          center = (x + w//2, y + h//2)
                          frame = cv2.ellipse(self.colour, center, (w//2, h//2), 0, 0, 360, colour, 1)
                      cv2.imshow(self.windowName, self.colour)

          elif pressed == 104: # 'h' for hough
            angleres = (self.houghAngleResolution * np.pi)/180
            lines = cv2.HoughLinesP(self.cur, self.houghDistanceResolution, angleres, self.houghStrength, self.houghMinLL, self.houghMaxLG)
            if lines is None or len(lines) == 0:
                print('hough found no lines')
                cv2.imshow(self.windowName, self.cur)
            else:
                print('hough found %d lines' % len(lines))
                self.colour = cv2.cvtColor(self.cur, cv2.COLOR_GRAY2BGR)
                self.drawLinesOnImg(lines, self.colour)
                cv2.imshow(self.windowName, self.colour)
          elif pressed == 107: # 'k' for head
              if self.coords is None:
                  print('you need box coordinates for this')
              else:
                  if trajectory is not None:
                      print('using %s corner for box' % trajectory)
                      box = self.shift_coords(self.coords, trajectory)
                      topleft = (int(box[0]), int(box[2]))
                      bottomright = (int(box[1]), int(box[3]))
                      self.coords = box
                      self.colour = cv2.cvtColor(self.cur, cv2.COLOR_GRAY2BGR)
                      cv2.rectangle(self.colour, topleft, bottomright, (255, 0, 0), 1)
                      cv2.imshow(self.windowName, self.colour)
          elif pressed == 108: # 'l' for label
            print('cat (a)rriving, (l)eaving, (n)o cat, (w)ait for next image?')
            label = cv2.waitKey(0)
            if label == 97:
                descstr = 'cat arriving'
            elif label == 108:
                descstr = 'cat leaving'
            elif label == 110:
                descstr = 'no cat'
            elif label == 119:
                descstr = 'not sure what exactly'
            else: descstr = 'an unknown object'
            coordstr = 'unknown'
            if self.coords:
                w, h, _ = self.cur.shape
                width_factor = self.base_resolution[0]/w
                height_factor = self.base_resolution[1]/h
                normalised_coords = (self.coords[0] * width_factor,
                        self.coords[1] * width_factor,
                        self.coords[2] * height_factor,
                        self.coords[3] * height_factor)
                coordstr = ','.join(str(int(x)) for x in normalised_coords)
            print('image %s shows %s at %s' % (self.filename, descstr, coordstr))
            self.labelfile.write('%s,%s,%s\n' % (self.filename, descstr, coordstr))
          elif pressed == 109: # 'm' for mog2 background subtraction
              print('109: mog2')
              if self.snap is None:
                  print('Need a snapshot for this')
              else:
                  backsub = cv2.createBackgroundSubtractorMOG2()
                  # KNN just gets me a blank image
                  # backsub = cv2.createBackgroundSubtractorKNN()

                  # This adds just one background snapshot, might work better
                  # if I use several plus if I pre-process them all the same way
                  # (e.g. equalize hist)
                  backsub.apply(self.snap)
                  fgmask = backsub.apply(self.cur)
                  print('got here')
                  cv2.imshow(self.windowName, fgmask)
          elif pressed == 110: # 'n' for snapshot
              f = './imageextracts/' + '{0}-modified.jpg'.format(self.filename)
              self.colour = cv2.cvtColor(self.cur, cv2.COLOR_GRAY2BGR)
              cv2.imwrite(f, self.colour)
              print('saved image to %s' % f)
          elif pressed == 111: # 'o' for contours
            contours, hierarchy = cv2.findContours(self.cur, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            self.colour = cv2.cvtColor(self.cur, cv2.COLOR_GRAY2BGR)
            self.colour = cv2.drawContours(self.colour, contours, -1, (0, 255, 0), 1)
            #for index, c in enumerate(contours):
            #    ar = cv2.contourArea(c)
            #    if ar >= self.contourMinSize:
            #      print('area of contour %d is %f' % (index, ar))
            #      (x1,y1,x2,y2) = cv2.boundingRect(c)
            #      # self.colour = cv2.drawContours(self.colour, contours, index, (0, 255, 0), 1)
            #      self.colour = cv2.rectangle(self.colour, (x1,y1), (x2,y2), (0, 255, 0), 1)
            cv2.imshow(self.windowName, self.colour)
          elif pressed == 112: # 'p' for predict
              if self.cat_detector is None:
                  print('you need a cat detector for that')
              else:
                  retval = self.cat_detector.evaluate_motion_and_image(self.motion, self.cur)
                  print('detector says %s' % retval)
          elif pressed == 114: # 'r' for reset
            self.cur = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            cv2.imshow(self.windowName, self.cur)
          elif pressed == 115: # 's' for subtract snapshot
            # This is 'naive' background subtraction, also try  'm' for mog2
            if self.snap is not None:
                self.cur = cv2.absdiff(self.cur, self.snap)
                cv2.imshow(self.windowName, self.cur)
            else:
                print('no snapshot provided')
          elif pressed == 116: # 't' for threshold
            # Non-adaptive, but seems to do reasonably well?
            # Can invert this for better contour finding (pass 1 as last param, or THRESH_BINARY_INV)
            ret, self.cur = cv2.threshold(self.cur, 127, 255, cv2.THRESH_BINARY)
            cv2.imshow(self.windowName, self.cur)
          elif pressed == 117: # 'u' for inverted threshold
            ret, self.cur = cv2.threshold(self.cur, 127, 255, cv2.THRESH_BINARY_INV)
            cv2.imshow(self.windowName, self.cur)
          elif pressed == 120: # 'x' for extract
              if self.coords is None:
                  print('need to find a rectangle roi first')
              else:
                  gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                  y1 = int(min(self.coords[2], self.coords[3]))
                  if y1 >= 20:
                      y1 -= 20
                  else:
                      y1 = 0
                  y2 = int(max(self.coords[2], self.coords[3]))
                  y2 += 20
                  x1 = int(min(self.coords[0], self.coords[1]))
                  x2 = int(max(self.coords[0], self.coords[1]))
                  if x1 >= 20:
                      x1 -= 20
                  else:
                      x1 = 0
                  x2 += 20
                  print('coords for subimage: %d %d %d %d' % (x1, x2, y1, y2))
                  self.cur = gray[y1:y2, x1:x2]
                  cv2.imshow(self.windowName, self.cur)

        cv2.destroyAllWindows()

