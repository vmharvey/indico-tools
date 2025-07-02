from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import argparse
import logging
import sys
import time

import requests
import yaml

from indico import Event


class Clock():
  """Helper class to fetch the current time from the system clock. The returned
  time can be configured such that it is with respect to a spoofed system clock
  started when the class was first instantiated. This is useful for testing.
  """

  INIT_TIME = None

  def __init__(self, timezone: str, simulated_start: str = None):
    self.tz = ZoneInfo(timezone)

    if Clock.INIT_TIME == None:
      Clock.INIT_TIME = datetime.now(tz = self.tz)

    if simulated_start:
      self.sim_start = datetime.fromisoformat(simulated_start)
      self.sim_start = self.sim_start.replace(tzinfo = self.tz)
    else:
      self.sim_start = None

  @property
  def time(self):
    true_time = datetime.now(tz = self.tz)
    if self.sim_start is None:
      return true_time
    else:
      return self.sim_start + (true_time - self.INIT_TIME)


class SlackChannel():
  """Interface to a single Slack channel via a pre-configured webhook URL,
  with methods for announcing sessions and talks in the specific Slack message
  format.
  """

  def __init__(self, webhook_url: str):
    self.webhook_url = webhook_url

  def _fmt_time(self, dt: datetime):
    # return dt.strftime('%I:%M') # 01:00
    return dt.strftime('%I').lstrip('0') + dt.strftime(':%M') # 1:00

  def _fmt_time_xx(self, dt: datetime):
    # return dt.strftime('%I:%M %p') # 01:00 AM
    return dt.strftime('%I').lstrip('0') + dt.strftime(':%M %p') # 1:00 AM

  def announce_session(self, session: dict):
    title = session['title']
    url = session['url']
    room = session['room']

    start = session['startDate']
    end = session['endDate']

    conveners = session['conveners']
    if len(conveners) > 0:
      convener_string = ", ".join([build_name(n) for n in conveners])
    else:
      convener_string = "N/A"

    # The session link has tabs for each day, and we can switch to the correct
    # tab for this day by doing this
    better_url = f"{url}#{start.strftime('%Y%m%d')}"

    mrkdwn_text = "\n".join([
      f"*Convener{'s' if len(conveners) > 1 else ''}:* {convener_string}",
      f"<{better_url}|Click here to view the session timetable>",
    ])

    # Block Kit Builder: https://app.slack.com/block-kit-builder/T01CDMTHALA
    payload = {
      'blocks': [
        {
          'type': 'header',
          'text': {
            'type': 'plain_text',
            'text': f'Starting session "{title}" in {room}',
            'emoji': True
          }
        },
        {
          'type': 'section',
          'text': {
            'type': 'mrkdwn',
            'text': mrkdwn_text,
          },
        },
      ],
    }
    r = requests.post(self.webhook_url, json = payload)
    r.raise_for_status()

  def announce_talk(self, session: dict, talk: dict):
    room = session['room']
    title = talk['title']
    url = talk['url']
    start = talk['startDate']
    end = talk['endDate']

    speakers = talk['speakers']
    speaker_string = ", ".join([build_name(n) for n in speakers])

    material = talk['material']

    mrkdwn_text = "\n".join([
      f"_Talk scheduled from {self._fmt_time(start)}–{self._fmt_time_xx(end)} in {room}_",
      f"*Title:* <{url}|{title}>",
      f"*Speaker{'s' if len(speakers) > 1 else ''}:* {speaker_string}",
    ])

    # Block Kit Builder: https://app.slack.com/block-kit-builder/T01CDMTHALA
    payload = {
      'blocks': [
        {
          'type': 'section',
          'text': {
            'type': 'mrkdwn',
            'text': mrkdwn_text,
          },
        },
        {
          'type': 'divider',
        },
      ],
    }
    r = requests.post(self.webhook_url, json = payload)
    r.raise_for_status()


def build_name(indico_name: dict):
  """Construct a person's full name from an Indico API results structure
  containing the details of one person.
  """
  try:
    full_name = []
    if 'title' in indico_name:
      full_name.append(indico_name['title'])
    full_name.append(indico_name['first_name'])
    full_name.append(indico_name['last_name'])
    return " ".join(full_name)
  except KeyError:
    logger.error(f"Error when trying to build name {indico_name}")
    return '-'


def choose_one_room(sessions: list):
  """Prompt the user to select one room from a list of all unique rooms that
    appear in use for conference sessions.
  """
  all_rooms = [sess['room'] for sess in sessions]
  all_rooms = set(all_rooms)
  all_rooms = sorted(all_rooms)
  room_dict = dict(zip(range(len(all_rooms)), all_rooms))

  print("Select a room to monitor")
  for i_choice,value in room_dict.items():
    print(f"{i_choice}: {value}")
  while True:
    try:
      choice = input("[0]: ")
      if len(choice) == 0:
        choice = 0
      else:
        choice = int(choice)
    except ValueError:
      print("Type a valid integer")
      continue
    else:
      if 0 <= choice < len(room_dict):
        break
      else:
        print("Type a valid integer")
        continue

  return room_dict[choice]


def main():
  # Parse command line
  parser = argparse.ArgumentParser(
    description = "Announce sessions and contributions to dedicated Slack channels")
  parser.add_argument('-c', '--config', type = str,
    default = 'config.yaml', help = "configuration file")
  parser.add_argument('-d', '--debug', action = 'store_true',
    help = "write debug information to the terminal")
  parser.add_argument('-s', '--simulated-start-time', type = str,
    default = None, help = "spoof the system clock as if it read this time"
    "when the script started. Use ISO 8601 timestamp format YYYY-MM-DDTHH:MM:SS."
    "The event timezone will be assumed")
  parser.add_argument('-k', '--schedule-delay', type = int,
    default = 0, help = "delay the announcement of talks other than the first"
    "in each session by this many minutes (default: 0)")
  args = parser.parse_args()

  # Set up logging
  logger = logging.getLogger(__name__)
  logger.setLevel(logging.DEBUG if args.debug else logging.INFO)
  logging.basicConfig(format='%(levelname)s %(message)s')
  logging.captureWarnings(True)

  # Simple hack to make log level names have a bit of colour on the terminal
  if sys.stdout.isatty():
    logging.addLevelName(logging.DEBUG,    "\x1b[1;35m[DEBUG]\x1b[0m")
    logging.addLevelName(logging.INFO,     "\x1b[1;34m[INFO]\x1b[0m ")
    logging.addLevelName(logging.WARNING,  "\x1b[1;36m[WARN]\x1b[0m ")
    logging.addLevelName(logging.ERROR,    "\x1b[1;31m[ERROR]\x1b[0m")
    logging.addLevelName(logging.CRITICAL, "\x1b[1;31m[FATAL]\x1b[0m")
  else:
    logging.addLevelName(logging.DEBUG,    "[DEBUG]")
    logging.addLevelName(logging.INFO,     "[INFO] ")
    logging.addLevelName(logging.WARNING,  "[WARN] ")
    logging.addLevelName(logging.ERROR,    "[ERROR]")
    logging.addLevelName(logging.CRITICAL, "[FATAL]")

  if args.simulated_start_time:
    logger.debug(f"Will spoof system clock to {args.simulated_start_time}")
  if args.schedule_delay:
    logger.debug(f"Will delay talk announcements by {args.schedule_delay} minutes")

  with open(args.config) as config_file:
    config = yaml.load(config_file, Loader = yaml.Loader)

  api_token = config['indico']['api_token']
  event_id = config['indico']['event_id']
  event_timezone = config['indico']['event_timezone']
  channel_map = config['slack']['channel_map']

  event = Event(event_id = event_id, api_token = api_token, timezone = event_timezone)
  channels = {k: SlackChannel(v) for k,v in config['slack']['webhooks'].items()}

  logger.debug("Fetching session information...")
  sessions = event.get_sessions()
  logger.debug("Done")

  # Clean up the data structure
  for sess in sessions:
    del sess['conference'] # Noisy duplication of top-level conference info

  room_choice = choose_one_room(sessions)
  print("Selected:", room_choice)

  # Start the simulated clock now, or just set up the real clock
  clock = Clock(timezone = event_timezone, simulated_start = args.simulated_start_time)
  schedule_delay = timedelta(minutes = args.schedule_delay)

  for sess in sessions:
    session_title = sess['title']
    room = sess['room']
    session_start = sess['startDate']
    session_end = sess['endDate']
    contributions = sess['contributions']
    # Maybe useful for filtering
    type_title = sess['session']['title']
    slot_title = sess['slotTitle']

    if len(session_title) > 37:
      session_title_log = session_title[:37] + "..."
    else:
      session_title_log = session_title

    if room != room_choice:
      continue
    if clock.time > session_end:
      continue

    try:
      channel_name = channel_map[room]
    except KeyError:
      raise RuntimeError(f"Configuration does not have a mapping of room '{room}'"
        "to a Slack channel")

    logger.debug(f"Time is {clock.time}")

    if clock.time < session_start:
      logger.info(f"Waiting until {session_start} to announce session '{session_title_log}'")
      while True:
        if clock.time < session_start:
          time.sleep(1)
        else:
          break

      channels[channel_name].announce_session(sess)
    else:
      logger.info(f"Ignoring session '{session_title_log}' that has already started")

    logger.debug(f"{type_title=}")
    logger.debug(f"{slot_title=}")

    for talk in contributions:
      talk_title = talk['title']
      talk_start = talk['startDate']
      talk_end = talk['endDate']
      talk_type = talk['type']

      if len(talk_title) > 37:
        talk_title_log = talk_title[:37] + "..."
      else:
        talk_title_log = talk_title

      if clock.time > talk_end:
        continue
      if talk_type in config['indico']['slack_filters'].get('contribution', {}).get('type', []):
        logger.debug(f"Skipping contribution with filtered type {talk_type}")
        continue

      logger.debug(f"Time is {clock.time}")

      if talk_start == session_start:
        logger.info(f"Announcing '{talk_title_log}' first in the session")
        channels[channel_name].announce_talk(sess, talk)
      elif clock.time < talk_start + schedule_delay:
        logger.info(f"Waiting until {talk_start + schedule_delay} to announce talk '{talk_title_log}'")
        while True:
          if clock.time < talk_start + schedule_delay:
            time.sleep(1)
          else:
            break
        channels[channel_name].announce_talk(sess, talk)
      else:
        logger.info(f"Ignoring talk '{talk_title_log}' that has already started")

if __name__ == "__main__":
  main()
