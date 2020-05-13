import argparse
import cv2
from datetime import date, datetime
import os
import re

import events_from_log
from cat_detector import CatDetector
from explorer import imageExplorer


def list_events_for_date(imagedir, date_to_show):
    datestr = date_to_show.strftime('%Y%m%d')
    p = re.compile('(\d+)-' + datestr + '(\d+)-(\d+).jpg')
    events = {}
    for file in os.listdir(imagedir):
        m = re.match(p, file)
        if m:
            event_id = m.group(1)
            timeofday = m.group(2)
            idx = m.group(3)
            if event_id not in events:
                events[event_id] = []
            events[event_id].append({'timeofday': timeofday,
                'id': event_id,
                'datetime': datestr + timeofday,
                'idx': idx,
                'filename': file})
    for k, v in events.items():
        v.sort(key=events_from_log.eventkey)
    return events


def list_images(imagedir, date_to_show):
    events = list_events_for_date(imagedir, date_to_show)
    if not events:
        print('No events for %s' % date_to_show.strftime('%Y-%m-%d'))
    print('There are %d events: ' % len(events))
    keys = list(events.keys())
    keys.sort()
    for k in keys:
        print(k)
        x = events[k][0]
        print('first img %s at %s' % (x['filename'], x['timeofday']))


def show_single_image(filename, detector):
    img = cv2.imread(filename)
    if img is None:
        print('failed to read image at %s' % filename)
        return
    cv2.imshow(filename, img)
    pressed = cv2.waitKey(0)
    if pressed == 112: # 'p'
        if detector is None:
            print('you need a cat detector for this')
        else:
            retval = detector.evaluate_motion_and_image(None, img)
            print('detector says: %s' % retval)
    elif pressed == 120: # 'x'
        xp = imageExplorer(filename, detector, labelfile)
        xp.exploreImage(img, None, None, None)
    cv2.destroyAllWindows()


def show_images_no_log(imagedir, date_to_show, idx, labelfile, detector):
    ev = list_events_for_date(imagedir, date_to_show)
    if idx not in ev:
        print('no event %s for date %s' % (idx, date_to_show))
        return
    windowname = '%s' % date_to_show
    i = 0
    img = cv2.imread(imagedir + ev[idx][i]['filename'])
    if img is None:
        print('failed to read image at %s' % ev[idx][i]['filename'])
        return
    cv2.imshow(windowname, img)
    while(1):
        pressed = cv2.waitKey(0)
        if pressed == 83: # cursor right
            if i+1 >= len(ev[idx]):
                print('at last image')
                continue
            else:
                i += 1
        elif pressed == 81: # cursor left
            if i == 0:
                print('at first image')
                continue
            else:
                i -= 1
        elif pressed == 112: # 'p'
            if detector is None:
                print('you need a cat detector for this')
            else:
                retval = detector.evaluate_motion_and_image(None, img)
                print('detector says: %s' % retval)
        elif pressed == 120: # 'x'
            xp = imageExplorer(ev[idx][i]['filename'], detector, labelfile)
            xp.exploreImage(img, None, None, None)
        else:
            break
        print('showing image %d of %d' % (i, len(ev[idx])))
        img = cv2.imread(imagedir + ev[idx][i]['filename'])
        cv2.imshow(windowname, img)
    cv2.destroyAllWindows()
        

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
  parser.add_argument('--picture', default=None, help='Single picture filename')
  parser.add_argument('--labelfile', default='/tmp/catlabels.csv', help='Where to write labels')
  parser.add_argument('--daemonlog', default=None, help='File with cat flap daemon log messages')
  parser.add_argument('--modelfile', default=None, help='File to load model from')
  args = parser.parse_args()
  date_to_show = None
  if not args.date and args.daemonlog is not None:
      with open(args.daemonlog) as daemonfile:
          daemon_events = events_from_log.daemonlog_datelist(daemonfile)
          print(daemon_events)
          exit()
  elif args.date == 'today' or args.date is None:
    date_to_show = date.today()
  else:
    date_to_show = datetime.strptime(args.date, "%Y-%m-%d").date()
  daemon_events = None
  if args.daemonlog is not None:
      with open(args.daemonlog) as daemonfile:
          daemon_events, snapshots = events_from_log.daemonlog_events_for_date(daemonfile, date_to_show)
  if args.idx is None and args.picture is None:
      if daemon_events is not None:
          for event_id, events in daemon_events.items():
              print('event_id: %s started at %s' % (event_id, events[0]['motiontime']))
      else:
          list_images(args.images, date_to_show)
      exit()
  if not os.path.exists(args.labelfile):
      with open(args.labelfile, 'w') as labelfile:
          labelfile.write('filename,action,left,right,top,bottom')
  cat_detector = None
  if args.modelfile is not None:
      CatDetector.setupCatDetector(args.modelfile, None)
      cat_detector = CatDetector.makeCatDetector()
  with open(args.labelfile, 'a') as labelfile:
      if args.picture is not None:
          show_single_image(args.picture, cat_detector)
      elif daemon_events is not None:
          show_image(args.images, daemon_events, snapshots, args.idx, cat_detector, labelfile)
      else:
          show_images_no_log(args.images, date_to_show, args.idx, labelfile, cat_detector)
    
