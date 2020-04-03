import argparse
import cv2
from datetime import date, datetime
import os
import re
import sys

from explorer import imageExplorer

PICTURES_DIR='./images/'

def eventkey(event):
  return event['timeofday'] + event['idx']
    
def list_events_for_date(date_to_show):
  datestr = date_to_show.strftime('%Y%m%d')
  p = re.compile('(\d+)-' + datestr + '(\d+)-(\d+).jpg')
  events = {}

  for file in os.listdir(PICTURES_DIR):
    m = re.match(p, file)
    if m:
      event_id = m.group(1)
      timeofday = m.group(2)
      idx = m.group(3)
      if event_id not in events:
        events[event_id] = []
      events[event_id].append({'timeofday': timeofday, 'idx': idx, 'filename': file})
      
  for k, v in events.items():
    v.sort(key=eventkey)

  return events


def list_images(date_to_show):
  events = list_events_for_date(date_to_show)
  if not events:
    print("No events for %s." % date_to_show.strftime('%Y-%m-%d'))
  print("There are %d events: " % len(events))
  keys = list(events.keys())
  keys.sort()
  for k in keys:
    print(k)
    x = events[k][0]
    print("first img %s at %s:%s:%s" % (x['filename'], x['timeofday'][0:2], x['timeofday'][2:4], x['timeofday'][4:6]))


def show_image(date_to_show, idx):
  ev = list_events_for_date(date_to_show)
  if idx not in ev:
    print('no event %s for date %s' % (idx, date_to_show))
    return
  i = 0
  img = cv2.imread(PICTURES_DIR + ev[idx][i]['filename'])
  windowname = '%s: %s' % (idx, date_to_show)
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
    elif pressed == 120: # 'x'
      xp = imageExplorer()
      xp.exploreImage(img)
    else:
      break
    print('showing image %d of %d' % (i, len(ev[idx])))
    img = cv2.imread(PICTURES_DIR + ev[idx][i]['filename'])
    cv2.imshow(windowname, img)
  cv2.destroyAllWindows()


if __name__ == "__main__":
  parser = argparse.ArgumentParser('view camera images')
  parser.add_argument('--date', default=None, help='The day to show images for')
  parser.add_argument('--idx', default=None, help='The event to show images for')
  args = parser.parse_args()
  date_to_show = None
  if not args.date or args.date == 'today':
    date_to_show = date.today()
  else:
    date_to_show = datetime.strptime(args.date, "%Y-%m-%d").date()
  if args.idx is None:
    list_images(date_to_show)
  else:
    show_image(date_to_show, args.idx)
  
  
  
