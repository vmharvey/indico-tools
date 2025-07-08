import argparse
import json
import logging
import sys

import yaml

from indico import Event

protection_message = "The organisers have restricted access to this material to registrants only"

def main():
  # Parse command line
  parser = argparse.ArgumentParser(
    description = "Update permissions of all presentation material in the event")
  parser.add_argument('-c', '--config', type = str,
    default = 'config.yaml', help = "configuration file")
  parser.add_argument('-d', '--debug', action = 'store_true',
    help = "write debug information to the terminal")
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

  with open(args.config) as config_file:
    config = yaml.load(config_file, Loader = yaml.Loader)

  api_token = config['indico']['api_token']
  event_id = config['indico']['event_id']
  event_timezone = config['indico']['event_timezone']

  event = Event(event_id = event_id, api_token = api_token, timezone = event_timezone)
  sessions = event.get_sessions()
  regs = event.get_registration_forms()

  if len(regs) == 0:
    raise RuntimeError("No registration forms returned")

  if len(regs) > 1:
    raise RuntimeError("Not sure what to do with multiple registration forms."
      f"Do I use one or all of them? I saw: {regs}")

  reg_ident = regs[0]['identifier']

  for sess in sessions:
    for cont in sess['contributions']:
      for folder in cont['folders']:
        folder_id = int(folder['id'])
        logger.debug(f"Contribution: {cont['url']}, folder: {folder_id}")

        for attach in folder['attachments']:
          if not attach['is_protected']:
            desc = [protection_message]
            # Keep the existing description as well if there is one
            if attach['description']:
              logger.debug(f"Keeping existing description: {attach['description']}")
              desc.insert(0, attach['description'])

            logger.info(f"Protecting {attach.get('filename', 'NONE')} with ACL '{reg_ident}'")
            event.update_attachment(attach, {
                # NOTE: This description appears on hover, everyone sees it,
                # even when not logged in
                'description': ".\n\n".join(desc),
                'protected': 'y',
                'acl': json.dumps([reg_ident]),
              },
            )

if __name__ == "__main__":
  main()
