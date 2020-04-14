import argparse
import os
from trainer import Trainer


if __name__ == "__main__":
  parser = argparse.ArgumentParser('view camera images')
  parser.add_argument('--labelfile', default='/tmp/catlabels.csv', help='Training data')
  parser.add_argument('--testfile', default=None, help='Test data')
  # If training, models will be written to this file.
  # For testing, models will be loaded from this file.
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
          trainer.addTrainingDataFromFile(labelfile)
      print('collected training data')
      trainer.trainClassifier()
      print('Finished training model')
      # This just tests on the training data
      trainer.testClassifier()
      if args.modelfile:
          trainer.saveModels(args.modelfile)

  if testing:
      if not trainer.model:
          if not args.modelfile:
              print('Need to train a model or load one')
              exit
          trainer.loadModels(args.modelfile)
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


