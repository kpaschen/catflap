import cv2
import numpy as np

class imageExplorer:
    def onCannyTrackbar(self, x):
        # The trackbar always starts at 0, but 3 is the lowest legal value for aperture.
        if x <= 3:
            x = 3
        self.cannyAperture = x

    def onHoughMinLLTrackbar(self, x):
        self.houghMinLL = x

    def onHoughMaxLGTrackbar(self, x):
        self.houghMaxLG = x

    def onHoughStrengthTrackbar(self, x):
        self.houghStrength = x

    def onContourMinSize(self, x):
        self.contourMinSize = x

    def __init__(self, filename, labelfile):
        self.windowName = 'Processed image'
        self.cannyAperture = 3
        self.houghMinLL = 25
        self.houghMaxLG = 35
        self.houghStrength = 40
        self.contourMinSize = 30
        self.filename = filename
        self.coords = None
        self.labelfile = labelfile
        cv2.namedWindow(self.windowName)
        cv2.createTrackbar('Canny aperture size', self.windowName, self.cannyAperture, 9, self.onCannyTrackbar)
        cv2.createTrackbar('Hough min line length', self.windowName, self.houghMinLL, 100, self.onHoughMinLLTrackbar)
        cv2.createTrackbar('Hough max line gap', self.windowName, self.houghMaxLG, 100, self.onHoughMaxLGTrackbar)
        cv2.createTrackbar('Hough strength', self.windowName, self.houghStrength, 200, self.onHoughStrengthTrackbar)
        cv2.createTrackbar('Contour min size', self.windowName, self.contourMinSize, 2000, self.onContourMinSize)

    def drawLinesOnImg(self, lines, img):
        left = 400
        right = 0
        top = 240
        bottom = 0
        for points in lines:
            print(points[0])
            p = points[0]
            if p[0] < left:
                left = p[0]
            if p[1] < top:
                top = p[1]
            if p[2] > right:
                right = p[2]
            if p[3] > bottom:
                bottom = p[3]
            cv2.line(img, (p[0],p[1]), (p[2],p[3]), (0, 0, 255), 1)
        self.coords = (left, right, top, bottom)
        print('left %d, right %d, top %d, bottom %d' % (left, right, top, bottom))
        
    def exploreImage(self, img):
        self.cur = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cv2.imshow(self.windowName, self.cur)
        print('shell: q to quit, c canny, h find lines with hough, t threshold, o contours, r reset')

        while(1):
          pressed = cv2.waitKey(0)
          print(pressed)
          if pressed == 113: # 'q' for quit
              break
          elif pressed == 99: # 'c' for canny
            self.cur = cv2.Canny(self.cur, 100, 200, self.cannyAperture)
            cv2.imshow(self.windowName, self.cur)
          elif pressed == 101: # 'e' equalizeHist
            self.cur = cv2.equalizeHist(self.cur)
            cv2.imshow(self.windowName, self.cur)
          elif pressed == 104: # 'h' for hough
            lines = cv2.HoughLinesP(self.cur, 1, np.pi/180, self.houghStrength, self.houghMinLL, self.houghMaxLG)
            if lines is None or len(lines) == 0:
                print('hough found no lines')
                cv2.imshow(self.windowName, self.cur)
            else:
                print('hough found %d lines' % len(lines))
                self.colour = cv2.cvtColor(self.cur, cv2.COLOR_GRAY2BGR)
                self.drawLinesOnImg(lines, self.colour)
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
            coordstr = ','.join(str(x) for x in self.coords) if self.coords else 'unknown'
            print('image %s shows %s at %s' % (self.filename, descstr, coordstr))
            self.labelfile.write('%s,%s,%s\n' % (self.filename, descstr, coordstr ))
          elif pressed == 111: # 'o' for contours
            contours, hierarchy = cv2.findContours(self.cur, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            self.colour = cv2.cvtColor(self.cur, cv2.COLOR_GRAY2BGR)
            for index, c in enumerate(contours):
                ar = cv2.contourArea(c)
                if ar >= self.contourMinSize:
                  print('area of contour %d is %f' % (index, ar))
                  (x1,y1,x2,y2) = cv2.boundingRect(c)
                  # self.colour = cv2.drawContours(self.colour, contours, index, (0, 255, 0), 1)
                  self.colour = cv2.rectangle(self.colour, (x1,y1), (x2,y2), (0, 255, 0), 1)
            cv2.imshow(self.windowName, self.colour)
          elif pressed == 114: # 'r' for reset
            self.cur = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            cv2.imshow(self.windowName, self.cur)
          elif pressed == 116: # 't' for threshold
            # Non-adaptive, but seems to do reasonably well?
            ret,self.cur = cv2.threshold(self.cur, 127, 255, cv2.THRESH_BINARY)
            cv2.imshow(self.windowName, self.cur)

        cv2.destroyAllWindows()

