import argparse
import cv2
import os
import numpy as np
import re
import sys

class Trainer(object):
    def __init__(self):
        self.features = []
        self.labels = []
        self.model = None

    def label_for_string(self, strlabel):
        if strlabel == 'cat arriving':
            return 3
        elif strlabel == 'cat leaving':
            return 2
        elif strlabel == 'not sure what exactly':
            return 1
        elif strlabel == 'no cat':
            return 0
        else:
            return 0

    def string_for_label(self, label):
        if label == 3:
            return 'cat arriving'
        elif label == 2:
            return 'cat leaving'
        elif label == 1:
            return 'not sure'
        elif label == 0:
            return 'no cat'

    def makeTrainingData(self):
        featurecount = len(self.features)
        if featurecount != len(self.labels):
            print('Must have same number of features and labels')
            return None
        f = np.ndarray((featurecount, 4), np.float32, np.array(self.features))
        l = np.asarray(self.labels).reshape((featurecount, 1))
        return (f, l)

    def addTrainingData(self, label, coords, img):
        self.labels.append(self.label_for_string(label))
        self.features.append([np.float32(int(c)) for c in coords])

    def trainClassifier(self):
        # self.model = cv2.ml.DTrees_create()
        self.model = cv2.ml.KNearest_create()
        samples, labels = self.makeTrainingData()
        self.model.train(samples=samples, layout=cv2.ml.ROW_SAMPLE, responses=labels)

    def saveModel(self, modelfile):
        if self.model:
            self.model.save(modelfile)
        else:
            print('No model to save')

    def loadModel(self, modelfile):
        if self.model:
            print('Loading new model from %s, overwriting existing one.' % modelfile)
        self.model = cv2.ml.DTRees.load(modelfile)

    def testClassifier(self):
        if not self.model:
            print('You have to train a model first')
            return
        featurecount=len(self.features)
        confmatrix = np.zeros((4,4), dtype=np.int32)
        goodcount = 0
        for index, sample in enumerate(self.features):
          f = np.ndarray((1, 4), dtype=np.float32, buffer=np.array(sample, dtype=np.float32))
          retval, results = self.model.predict(f)
          expected = self.labels[index]
          confmatrix[int(retval)][int(expected)] += 1
          if expected == retval:
              # print('index {0} ({2}): good: {1}'.format(index, self.string_for_label(retval), sample))
              goodcount += 1
          #else:
              # print('index {0} ({3}): bad: wanted {1} but got {2}'.format(index,
              #    self.string_for_label(expected),
              #    self.string_for_label(retval), sample))
        print('performance: {0} out of {1} = {2}'.format(goodcount, featurecount, (float)(goodcount)/featurecount))
        print('confusion matrix:\n ', confmatrix)


if __name__ == "__main__":
  parser = argparse.ArgumentParser('view camera images')
  parser.add_argument('--labelfile', default='/tmp/catlabels.csv', help='Training data')
  parser.add_argument('--testfile', default=None, help='Test data')
  # If training, model will be written to this file.
  # For testing, model will be loaded from this file.
  parser.add_argument('--modelfile', default='./catflapmodel', help='File with model')
  args = parser.parse_args()
  training = False
  testing = False
  if args.labelfile:
      training = True
      if not os.path.exists(args.labelfile):
          print('Missing file with training data')
          exit
  if args.testfile:
      testing = True
      if not os.path.exists(args.testfile):
          print('Missing file with test data')
          exit
  trainer = Trainer()
  if training:
      with open(args.labelfile, 'r') as labelfile:
          for line in labelfile:
              l = line.rstrip('\n')
              parts = l.split(',')
              if parts[0] == 'filename': # header line
                  continue
              if parts[2] == 'unknown':
                  continue
              trainer.addTrainingData(label=parts[1], coords=(parts[2],parts[3],parts[4],parts[5]), img=None)
      trainer.trainClassifier()
      print('Finished training model')
      # This just tests on the training data
      trainer.testClassifier()
      if args.modelfile:
          print('Saving model to %s' % args.modelfile)
          trainer.saveModel(args.modelfile)
  if testing:
      if not trainer.model:
          if not args.modelfile:
              print('Need to train a model or load one')
              exit
          trainer.loadModel(args.modelfile)
      with open(args.testfile, 'r') as testfile:
          for line in testfile:
              l = line.rstrip('\n')
              parts = l.split(',')
              if parts[0] == 'filename': # header line
                  continue
              if parts[2] == 'unknown':
                  continue
              coords = (parts[2],parts[3],parts[4],parts[5])
              print('For coords {0} expecting label {1}'.format(coords, parts[1]))
              trainer.testModel(coords=(parts[2],parts[3],parts[4],parts[5]))


