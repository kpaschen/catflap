import argparse
import cv2
from datetime import date, datetime
import os
import re
import sys

from explorer import imageExplorer

DEFAULT_IMAGE_PATH='/home/pi/pictures'

def eventkey(event):
  return event['timeofday'] + event['idx']
    
# Get all the days that this daemonlog has events for.
def daemonlog_datelist(daemonlogfile):
    p = re.compile('([\d]+-[\d]+-[\d]+)-([\d:]+) received message (.*)')
    dates = set()
    for line in daemonlogfile:
        m = re.match(p, line)
        if m is not None:
            dates.add(m.group(1))
    return dates


def hms_to_seconds(timeexpr):
    parts = [int(x) for x in timeexpr.split(':')[:-1]]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


# Populate and return events dict for one date based on daemonlogfile.
# Does not verify whether the corresponding image files exist.
def daemonlog_events_for_date(daemonlogfile, date_to_show):
    datestr = date_to_show.strftime('%Y-%m-%d')
    p = re.compile('(' + datestr + ')-([\d:]+) received message (.*)')
    events = {}
    savefilepattern = re.compile('saved (.*.jpg)')
    snapshotpattern = re.compile('saved (.*-snapshot.jpg)')
    motionpattern = re.compile('motion detected: (\d+) changed pixels (\d+) x (\d+) at (\d+) (\d+)')
    savefilename = re.compile(DEFAULT_IMAGE_PATH + '/([\d]+)-([\d]+)-([\d]+).jpg')
    current_event_id = -1
    pending_motion = None

    for line in daemonlogfile:
        m = re.match(p, line)
        if m is not None:
            # only 'save' messages will have the event id, but a motion
            # message may arrive before a save message. when
            # a new event starts, we almost always get the motion msg
            # first.
            ymd = m.group(1)
            timestamp = m.group(2)
            msg = m.group(3)
            parsed = re.match(snapshotpattern, msg)
            if parsed is not None:
                continue
            parsed = re.match(savefilepattern, msg)
            if parsed is not None:
                fileparts = re.match(savefilename, parsed.group(1))
                event_id = fileparts.group(1)
                datetime = fileparts.group(2)
                idx = fileparts.group(3)
                event_data = {
                        'id': event_id,
                        'datetime': datetime,
                        'timeofday': timestamp,
                        'idx': idx,
                        'filename': parsed.group(1).split('/')[-1]
                        }
                if event_id not in events:
                    current_event_id = int(event_id)
                    events[event_id] = []
                    if pending_motion is not None:
                        event_data.update(pending_motion)
                        pending_motion = None
                    events[event_id].append(event_data)
                    continue
                added_save = False
                if len(events[event_id]) > 0:
                    last_event = events[event_id][-1]
                    if 'idx' not in last_event:
                        last_event.update(event_data)
                        added_save = True
                if not added_save:
                    events[event_id].append(event_data)
            else:
                parsed = re.match(motionpattern, msg)
                if parsed is not None:
                    motiondata = {
                            'motiontime': timestamp,
                            'changedpixels': int(parsed.group(1)),
                            'width': int(parsed.group(2)),
                            'height': int(parsed.group(3)),
                            'x': int(parsed.group(4)),
                            'y': int(parsed.group(5))
                            }
                    if current_event_id == -1:
                        pending_motion = motiondata
                        continue
                    cur_event = events[event_id][-1]
                    if 'motiontime' in cur_event:
                        # Check if cur_event is more than a minute old.
                        # In that case, this is the first motion message of
                        # a new event.
                        evtime = hms_to_seconds(cur_event['timeofday'])
                        thistime = hms_to_seconds(timestamp)
                        if thistime - evtime < 60: 
                            events[event_id].append(motiondata)
                        else:
                            pending_motion = motiondata
                            current_event_id = -1
                            continue
                    else:
                        cur_event.update(motiondata)
                else:
                    print('bad message format: %s' % msg)
                    continue

    for _, v in events.items():
        v.sort(key=eventkey)
    return events


def find_snapshot_for_event(imagedir, event):
    x = datetime.strptime(event[0]['datetime'], '%Y%m%d%H%M%S')
    snapshottime = datetime(x.year, x.month, x.day, x.hour).strftime(
            '%Y%m%d%H%M%S')
    snapshotfilename = '{0}-{1}-snapshot.jpg'.format(event[0]['id'], snapshottime)
    if os.path.exists(imagedir + snapshotfilename):
        return cv2.imread(imagedir + snapshotfilename)
    elif os.path.exists(imagedir + 'lastsnap.jpg'):
        return cv2.imread(imagedir + 'lastsnap.jpg')
    print("No snapshot for %s" % snapshottime)
    return None


def show_image(imagedir, events, idx, labelfile):
  if idx not in events:
    print('no event %s in list' % idx)
    return
  i = 0
  img = cv2.imread(imagedir + events[idx][i]['filename'])
  if img is None:
    print('failed to find image at %s' % imagedir + events[idx][i]['filename'], flush=True)
  ev = events[idx][i]
  motion = (ev['changedpixels'], ev['width'], ev['height'], ev['x'], ev['y'])
  print('motion for this image: %s' % (motion,))
  windowname = idx
  cv2.imshow(windowname, img)
  snap = find_snapshot_for_event(imagedir, events[idx])
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
    elif pressed == 81: # cursor left
      if i == 0:
        print('at first image')
        continue
      else:
         i -= 1
         ev = events[idx][i]
    elif pressed == 120: # 'x'
      xp = imageExplorer(ev['filename'], labelfile)
      xp.exploreImage(img, snap, motion)
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
  args = parser.parse_args()
  date_to_show = None
  if not args.date:
      with open(args.daemonlog) as daemonfile:
          daemon_events = daemonlog_datelist(daemonfile)
          print(daemon_events)
          exit()
  elif args.date == 'today':
    date_to_show = date.today()
  else:
    date_to_show = datetime.strptime(args.date, "%Y-%m-%d").date()
  daemon_events = None
  with open(args.daemonlog) as daemonfile:
      daemon_events = daemonlog_events_for_date(daemonfile, date_to_show)
  if args.idx is None:
      for event_id, events in daemon_events.items():
          print('event_id: %s started at %s' % (event_id, events[0]['motiontime']))
  else:
     if not os.path.exists(args.labelfile):
         with open(args.labelfile, 'w') as labelfile:
             labelfile.write('filename,action,left,right,top,bottom')
     with open(args.labelfile, 'a') as labelfile:
         show_image(args.images, daemon_events, args.idx, labelfile)
    
