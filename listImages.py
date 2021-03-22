import argparse
import cv2
from datetime import date, datetime, timedelta
import os
import re

import events_from_log
from cat_detector import CatDetector
from explorer import imageExplorer


def list_dates(imagedir):
    p = re.compile('(\d+)-(\d+)-(\d+).jpg')
    dates = []
    for file in os.listdir(imagedir):
        m = re.match(p, file)
        if m:
            date_and_time = m.group(2)
            dt = datetime.strptime(date_and_time, '%Y%m%d%H%M%S')
            dates.append(date(dt.year, dt.month, dt.day))
    return dates


def list_events_for_date(imagedir, date_to_show):
    datestr = date_to_show.strftime('%Y%m%d')
    p = re.compile('(\d+)-' + datestr + '(\d+)-(\d+).jpg')
    s = re.compile('(\d+)-' + datestr + '(\d+)-snapshot.jpg')
    events = {}
    snapshots = {}
    for fname in os.listdir(imagedir):
        m = re.match(p, fname)
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
                'filename': fname})
        else:
            m2 = re.match(s, fname)
            if m2:
                event_id = m2.group(1)
                timeofday = m2.group(2)
                houroftheday = timeofday[0:2]
                snapshots[houroftheday] = {
                        'id': event_id,
                        'timeofday': timeofday,
                        'filename': fname}
    for k, v in events.items():
        v.sort(key=events_from_log.eventkey)
    return (events, snapshots)


def get_next_date_after(imagedir, curdate):
    try_this = curdate + timedelta(days=1)
    print('trying date %s' % try_this.strftime('%Y-%m-%d'))
    for i in range(30):
        (ev, snapshots) = list_events_for_date(imagedir, try_this)
        if ev:
            return (try_this, ev, snapshots)
        else:
            try_this = try_this + timedelta(days=1)
            print('no events for date %s' % try_this.strftime('%Y-%m-%d'))
    print('no events found for 30 days starting from %s' % curdate.strftime('%Y-%m-%d'))
    return (None, None, None)
            


def list_images(imagedir, date_to_show):
    (events, snapshots) = list_events_for_date(imagedir, date_to_show)
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


def loop_images_no_log(imagedir, date_to_start, labelfile, detector):
    if date_to_start is None:
        dates = list_dates(imagedir)
        if not dates:
            print('no events in %s' % imagedir)
            return
        curdate = dates[0]
    else:
        curdate = date_to_start
    (ev, snapshots) = list_events_for_date(imagedir, curdate)
    while(True):
        for idx in ev.keys():
            cont = show_images_no_log(imagedir, curdate, idx, labelfile, detector)
            if not cont:
                break
        (curdate, ev, snapshots) = get_next_date_after(imagedir, curdate)
        if ev:
            print('%d images found for %s' % (len(ev.keys()), curdate.strftime('%Y-%m-%d')))
            cont = input("Continue with next day? ")
            if (cont == 'n'):
                return
        else:
            return



def show_images_no_log(imagedir, date_to_show, idx, labelfile, detector):
    (ev, snapshots) = list_events_for_date(imagedir, date_to_show)
    if idx not in ev:
        print('no event %s for date %s' % (idx, date_to_show))
        return True
    windowname = '%s' % date_to_show
    i = 0
    filename = imagedir + ev[idx][i]['filename']
    img = cv2.imread(filename)
    if img is None:
        print('failed to read image at %s' % filename)
        return True
    cv2.imshow(windowname, img)
    print('showing image %d of %d' % (i, len(ev[idx])))
    while(1):
        pressed = cv2.waitKey(0)
        print(pressed)
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
        elif pressed == 108: # 'l'
            if not detector:
                print('you need a detector for this')
                continue
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
            coords = detector.get_coords(img)
            if coords:
                print(coords)
                coordstr = ','.join(str(x.astype(int)) for x in coords)
            print('image %s shows %s at %s' % (filename, descstr, coordstr))
            labelfile.write('%s,%s,%s\n' % (filename, descstr, coordstr))
        elif pressed == 112: # 'p'
            if detector is None:
                print('you need a cat detector for this')
            else:
                retval = detector.evaluate_motion_and_image(None, img)
                print('detector says: %s' % retval)
        elif pressed == 120: # 'x'
            xp = imageExplorer(ev[idx][i]['filename'], detector, labelfile)
            snapkey = ev[idx][i]['timeofday'][0:2]
            if snapkey in snapshots:
                snap = cv2.imread(imagedir + snapshots[snapkey]['filename'])
                xp.exploreImage(img, snap, None, None)
            else:
                xp.exploreImage(img, None, None, None)
        elif pressed == 116: # 't'
            return False
        else:
            break
        print('showing image %d of %d' % (i, len(ev[idx])))
        filename = imagedir + ev[idx][i]['filename']
        img = cv2.imread(filename)
        cv2.imshow(windowname, img)
    cv2.destroyAllWindows()
    return True
        

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
         if 'changedpixels' in ev:
             motion = (ev['changedpixels'], ev['width'], ev['height'], ev['x'], ev['y'])
             print('motion for this image: %s' % (motion,))
         else:
             motion = None
             print('missing motion for this image')
    elif pressed == 81: # cursor left
      if i == 0:
        print('at first image')
        continue
      else:
         i -= 1
         ev = events[idx][i]
         previous_motion = motion
         if 'changedpixels' in ev:
             motion = (ev['changedpixels'], ev['width'], ev['height'], ev['x'], ev['y'])
             print('motion for this image: %s' % (motion,))
         else:
             motion = None
             print('missing motion for this image')
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
  parser.add_argument('--loop', default=None, help='loop over all images in dir')
  args = parser.parse_args()
  date_to_show = None
  if not args.date and args.daemonlog is not None:
      with open(args.daemonlog) as daemonfile:
          daemon_events = events_from_log.daemonlog_datelist(daemonfile)
          print(daemon_events)
          exit()
  elif args.date == 'today':
    date_to_show = date.today()
  elif args.date is not None:
    date_to_show = datetime.strptime(args.date, "%Y-%m-%d").date()
  daemon_events = None
  if args.daemonlog is not None and date_to_show is not None:
      with open(args.daemonlog) as daemonfile:
          daemon_events, snapshots = events_from_log.daemonlog_events_for_date(daemonfile, date_to_show)
  if args.idx is None and args.picture is None and args.loop is None:
      if daemon_events is not None:
          for event_id, events in sorted(daemon_events.items()):
              print('event_id: %s started at %s' % (event_id, events[0]['motiontime']))
      elif date_to_show is not None:
          list_images(args.images, date_to_show)
      exit()
  if not os.path.exists(args.labelfile):
      with open(args.labelfile, 'w') as labelfile:
          labelfile.write('filename,action,left,right,top,bottom\n')
  cat_detector = None
  if args.modelfile is not None:
      CatDetector.setupCatDetector(args.modelfile, None)
      cat_detector = CatDetector.makeCatDetector()
  with open(args.labelfile, 'a') as labelfile:
      if args.picture is not None:
          show_single_image(args.picture, cat_detector)
      elif daemon_events is not None:
          show_image(args.images, daemon_events, snapshots, args.idx, cat_detector, labelfile)
      elif args.loop is not None:
          loop_images_no_log(args.images, date_to_show, labelfile, cat_detector)
      else:
          show_images_no_log(args.images, date_to_show, args.idx, None, labelfile, cat_detector)
    
