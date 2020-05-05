import argparse
import os
from trainer import Trainer


if __name__ == "__main__":
  parser = argparse.ArgumentParser('view camera images')
  parser.add_argument('--labelfile', default=None, help='Training data')
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
      if trainer.knn_model is None:
          print('need to make a knn model')
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
              if len(parts) < 6:
                  continue
              coords = (parts[2],parts[3],parts[4],parts[5])
              result = trainer.testModel(coords=(parts[2],parts[3],parts[4],parts[5]))
              reslabel = trainer.string_for_label(int(result))
              if parts[1] == reslabel:
                  continue
              print('File {0} coords {1} expecting label {2} and got {3}'.format(
                  parts[0], coords, parts[1], reslabel))


