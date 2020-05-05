import argparse
import cv2
from datetime import date, datetime
import os

import events_from_log
from cat_detector import CatDetector
from explorer import imageExplorer


def show_image(imagedir, events, snapshots, idx, detector, labelfile):
  if idx not in events:
    print('no event %s in list' % idx)
    return
  i = 0
  img = cv2.imread(imagedir + events[idx][i]['filename'])
  if img is None:
    print('failed to find image at %s' % imagedir + events[idx][i]['filename'], flush=True)
  ev = events[idx][i]
  motion = (ev['changedpixels'], ev['width'], ev['height'], ev['x'], ev['y'])
  previous_motion = None
  print('motion for this image: %s' % (motion,))
  windowname = idx
  cv2.imshow(windowname, img)
  snapkey = ev['datetime'][0:10]
  snap = None
  if snapkey in snapshots: 
      snap = cv2.imread(imagedir + snapshots[snapkey]['filename']+'-snapshot.jpg')
  elif os.path.exists(imagedir + 'lastsnap.jpg'):
      snap = cv2.imread(imagedir + 'lastsnap.jpg')
  if snap is not None:
      cv2.imshow('snapshot', snap)
  while(1):
    pressed = cv2.waitKey(0)
    if pressed == 83: # cursor right
      if i+1 >= len(events[idx]):
        print('at last image')
        continue
      else:
         i += 1
         ev = events[idx][i]
         previous_motion = motion
         motion = (ev['changedpixels'], ev['width'], ev['height'], ev['x'], ev['y'])
         print('motion for this image: %s' % (motion,))
    elif pressed == 81: # cursor left
      if i == 0:
        print('at first image')
        continue
      else:
         i -= 1
         ev = events[idx][i]
         previous_motion = motion
         motion = (ev['changedpixels'], ev['width'], ev['height'], ev['x'], ev['y'])
    elif pressed == 112: # 'p'
      if detector is None:
          print('you need a cat detector for this')
      else:
          retval = detector.evaluate_motion_and_image(motion, img)
          print('detector says: %s' % retval)
    elif pressed == 120: # 'x'
      xp = imageExplorer(ev['filename'], detector, labelfile)
      xp.exploreImage(img, snap, motion, previous_motion)
    else:
      break
    print('showing image %d of %d' % (i, len(events[idx])))
    img = cv2.imread(imagedir + ev['filename'])
    cv2.imshow(windowname, img)
  cv2.destroyAllWindows()


if __name__ == "__main__":
  parser = argparse.ArgumentParser('view camera images')
  parser.add_argument('--date', default=None, help='The day to show images for')
  parser.add_argument('--idx', default=None, help='The event to show images for')
  parser.add_argument('--images', default='./images/', help='Where your image files are')
  parser.add_argument('--labelfile', default='/tmp/catlabels.csv', help='Where to write labels')
  parser.add_argument('--daemonlog', default='./daemonlog', help='File with cat flap daemon log messages')
  parser.add_argument('--modelfile', default=None, help='File to load model from')
  args = parser.parse_args()
  date_to_show = None
  if not args.date:
      with open(args.daemonlog) as daemonfile:
          daemon_events = events_from_log.daemonlog_datelist(daemonfile)
          print(daemon_events)
          exit()
  elif args.date == 'today':
    date_to_show = date.today()
  else:
    date_to_show = datetime.strptime(args.date, "%Y-%m-%d").date()
  daemon_events = None
  with open(args.daemonlog) as daemonfile:
      daemon_events, snapshots = events_from_log.daemonlog_events_for_date(daemonfile, date_to_show)
  if args.idx is None:
      for event_id, events in daemon_events.items():
          print('event_id: %s started at %s' % (event_id, events[0]['motiontime']))
  else:
     if not os.path.exists(args.labelfile):
         with open(args.labelfile, 'w') as labelfile:
             labelfile.write('filename,action,left,right,top,bottom')
     cat_detector = None
     if args.modelfile is not None:
         CatDetector.setupCatDetector(args.modelfile, None)
         cat_detector = CatDetector.makeCatDetector()
     with open(args.labelfile, 'a') as labelfile:
         show_image(args.images, daemon_events, snapshots, args.idx, cat_detector, labelfile)
    
