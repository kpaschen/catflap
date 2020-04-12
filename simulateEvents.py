import argparse
import asyncio
import cv2
from datetime import date, datetime, time
import os
import re
from socket import AF_INET, socket, SOCK_DGRAM
import sys

async def send_msg(msg, addr):
    client_socket = socket(AF_INET, SOCK_DGRAM)
    client_socket.sendto(bytes(msg, 'utf8'), addr)


def eventkey(event):
  return event['timeofday'] + event['idx']
    

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
      events[event_id].append({'timeofday': timeofday, 'idx': idx, 'filename': file})
      
  for k, v in events.items():
    v.sort(key=eventkey)

  return events


async def simulate_event(imagedir, date_to_show, idx, addr):
  ev = list_events_for_date(imagedir, date_to_show)
  if idx not in ev:
    print('no event %s for date %s' % (idx, date_to_show))
    return
  i = 0
  imagefile = imagedir + ev[idx][i]['filename']
  basetime = ev[idx][i]['timeofday']
  bt = time.fromisoformat(basetime[0:2] + ':' + basetime[2:4] + ':' + basetime[4:6])
  b = datetime.combine(date.today(), bt)
  for i in range(1, len(ev[idx])):
      await send_msg(f'saved {imagefile}', addr)
      await send_msg('motion detected: 41725 changed pixels 304 x 216 at 181 108', addr)
      imagefile = imagedir + ev[idx][i]['filename']
      nexttime = ev[idx][i]['timeofday']
      nt = time.fromisoformat(nexttime[0:2] + ':' + nexttime[2:4] + ':' + nexttime[4:6])
      n = datetime.combine(date.today(), nt)
      sleeptime = (n - b).seconds
      print(f'sleeping for {sleeptime}')
      b = n
      await asyncio.sleep(sleeptime)


if __name__ == "__main__":
  parser = argparse.ArgumentParser('view camera images')
  parser.add_argument('--date', default=None, help='The day the images were taken')
  parser.add_argument('--idx', default=None, help='The event to replay')
  parser.add_argument('--images', default='./images/', help='Where your image files are')
  parser.add_argument('--host', default='127.0.0.1', help='Where the catflap daemon runs')
  parser.add_argument('--port', default=3333, help='Port of the catflap daemon')

  args = parser.parse_args()
  if args.idx is None:
      print(f'Need an event id')
      exit
  date_to_show = None
  if not args.date or args.date == 'today':
    date_to_show = date.today()
  else:
    date_to_show = datetime.strptime(args.date, "%Y-%m-%d").date()
  addr = (args.host, args.port)
  asyncio.run(simulate_event(args.images, date_to_show, args.idx, addr))
    
