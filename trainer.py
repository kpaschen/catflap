import cv2
import numpy as np
import re

class Trainer(object):
    def __init__(self):
        self.features = []
        self.labels = []
        self.knn_model = None
        self.dtree_model = None

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

    def addTrainingDataFromFile(self, trainfile):
        for line in trainfile:
            l = line.rstrip('\n')
            parts = l.split(',')
            if parts[0] == 'filename': # headerline
                continue
            if parts[2] == 'unknown':
                continue
            self.addTrainingData(label=parts[1], coords=(parts[2], parts[3], parts[4], parts[5]), img=None)

    def addTrainingData(self, label, coords, img):
        self.labels.append(self.label_for_string(label))
        self.features.append([np.float32(int(c)) for c in coords])

    def trainClassifier(self):
        samples, labels = self.makeTrainingData()
        # Removing the dtree model for now because I get a core dump when I try to train.
        # This could be something to do with my particular combination of opencv and other
        # packages?
        #self.dtree_model = cv2.ml.DTrees_create()
        #self.dtree_model.setMaxDepth(4)
        #self.dtree_model.train(samples=samples, layout=cv2.ml.ROW_SAMPLE, responses=labels)
        #print('dtree model trained')
        self.knn_model = cv2.ml.KNearest_create()
        self.knn_model.setDefaultK(2)
        samples, labels = self.makeTrainingData()
        self.knn_model.train(samples=samples, layout=cv2.ml.ROW_SAMPLE, responses=labels)
        print('knn model trained')

    def saveModels(self, modelfile):
        if self.dtree_model:
            filename = '{0}.dtree'.format(modelfile)
            print('saving dtree model to {0}'.format(filename))
            self.dtree_model.save('{0}'.format(filename))
        if self.knn_model:
            filename = '{0}.knn'.format(modelfile)
            print('saving knn model to {0}'.format(filename))
            self.knn_model.save('{0}'.format(filename))
        else:
            print('No model to save')

    def loadModels(self, modelfile):
        knn_file = '{0}.knn'.format(modelfile)
        dtree_file = '{0}.dtree'.format(modelfile)
        if os.path.exists(knn_file):
            if self.knn_model:
                print('Loading new knn model from %s, overwriting existing one.' % knn_file)
            self.knn_model = cv2.ml.KNearest_load(knn_file)
        if os.path.exists(dtree_file):
            if self.dtree_model:
                print('Loading new dtree model from %s, overwriting existing one.' % dtree_file)
            self.dtree_model = cv2.ml.DTRees_load(dtree_file)

    def testClassifier(self):
        if not self.dtree_model and not self.knn_model:
            print('You have to train a model first')
            return
        featurecount=len(self.features)
        confmatrix_dtree = np.zeros((4,4), dtype=np.int32)
        confmatrix_knn = np.zeros((4,4), dtype=np.int32)
        goodcount_dtree = 0
        goodcount_knn = 0
        for index, sample in enumerate(self.features):
          f = np.ndarray((1, 4), dtype=np.float32, buffer=np.array(sample, dtype=np.float32))
          if self.dtree_model:
              retval, results = self.dtree_model.predict(f)
              expected = self.labels[index]
              confmatrix_dtree[int(retval)][int(expected)] += 1
              if expected == retval:
                  goodcount_dtree += 1
          print('dtree performance: {0} out of {1} = {2}'.format(
              goodcount_dtree, featurecount, (float)(goodcount_dtree)/featurecount))
          print('dtree confusion matrix:\n ', confmatrix_dtree)
          if self.knn_model:
              retval, results = self.knn_model.predict(f)
              expected = self.labels[index]
              confmatrix_knn[int(retval)][int(expected)] += 1
              if expected == retval:
                  goodcount_knn += 1
          print('knn performance: {0} out of {1} = {2}'.format(
              goodcount_knn, featurecount, (float)(goodcount_knn)/featurecount))
          print('knn confusion matrix:\n ', confmatrix_knn)


