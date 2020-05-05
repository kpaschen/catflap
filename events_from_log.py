import datetime
import re

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


def make_snapshot_entry(long_filename):
    s = long_filename.split('/')[-1]
    snapshotfilename = re.compile('([\d]+)-([\d]+)')
    snap = re.match(snapshotfilename, s)
    snapshottime = datetime.datetime.strptime(snap.group(2), '%Y%m%d%H%M%S')
    snapshotbasetime = snapshottime.strftime('%Y%m%d%H')
    return {
            'id': snap.group(1),
            'filename': s,
            'timestamp': snap.group(2),
            'basetime': snapshotbasetime
            }


# Populate and return events dict for one date based on daemonlogfile.
# Does not verify whether the corresponding image files exist.
def daemonlog_events_for_date(daemonlogfile, date_to_show):
    datestr = date_to_show.strftime('%Y-%m-%d')
    p = re.compile('(' + datestr + ')-([\d:]+) received message (.*)')
    events = {}
    snapshots = {}
    savefilepattern = re.compile('saved (.*.jpg)')
    snapshotpattern = re.compile('saved (.*)-snapshot.jpg')
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
                snapshot = make_snapshot_entry(parsed.group(1))
                snapshots[snapshot['basetime']] = snapshot
                continue
            parsed = re.match(savefilepattern, msg)
            if parsed is not None:
                fileparts = re.match(savefilename, parsed.group(1))
                event_id = fileparts.group(1)
                dt = fileparts.group(2)
                idx = fileparts.group(3)
                event_data = {
                        'id': event_id,
                        'datetime': dt,
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
    return events, snapshots


