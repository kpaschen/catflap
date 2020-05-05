import argparse
import asyncio
import cv2
from datetime import date, datetime, time
import os
import re
from socket import AF_INET, socket, SOCK_DGRAM
import sys

import events_from_log

async def send_msg(msg, addr):
    client_socket = socket(AF_INET, SOCK_DGRAM)
    client_socket.sendto(bytes(msg, 'utf8'), addr)


async def simulate_event(imagedir, logfile, date_to_show, idx, addr):
  ev, _ = events_from_log.daemonlog_events_for_date(logfile, date_to_show)
  if idx not in ev:
    print('no event %s for date %s' % (idx, date_to_show))
    return
  basetime = 0
  for i in range(0, len(ev[idx])):
      imagefile = imagedir + ev[idx][i]['filename']
      imagetime = events_from_log.hms_to_seconds(ev[idx][i]['timeofday'])
      motiontime = events_from_log.hms_to_seconds(ev[idx][i]['motiontime'])
      motionmsg = 'motion detected: {0} changed pixels {1} x {2} at {3} {4}'.format(
          ev[idx][i]['changedpixels'],
          ev[idx][i]['width'],
          ev[idx][i]['height'],
          ev[idx][i]['x'],
          ev[idx][i]['y'])
      if motiontime > imagetime:
        await send_msg(f'saved {imagefile}', addr)
      await send_msg(motionmsg, addr)
      if motiontime <= imagetime:
        await send_msg(f'saved {imagefile}', addr)
      if i < len(ev[idx]) -1:
          nexttime = events_from_log.hms_to_seconds(ev[idx][i+1]['timeofday'])
          sleeptime = nexttime - max(imagetime, motiontime)
          print(f'sleeping for {sleeptime}')
          await asyncio.sleep(sleeptime)


if __name__ == "__main__":
  parser = argparse.ArgumentParser('view camera images')
  parser.add_argument('--date', default=None, help='The day the images were taken')
  parser.add_argument('--idx', default=None, help='The event to replay')
  parser.add_argument('--images', default='./images/', help='Where your image files are')
  parser.add_argument('--daemonlog', default='./daemonlog', help='Where your log messages are')
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
  with open(args.daemonlog) as daemonfile:
      asyncio.run(simulate_event(args.images, daemonfile, date_to_show, args.idx, addr))
    
