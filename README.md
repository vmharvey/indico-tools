# indico-tools

Some tools I wrote for automating aspects of the 2025 Annual Scientific Meeting of the Astronomical Society of Australia (ASA) hosted in Adelaide. They're somewhat generalised so they could be applicable to other events on Indico. They rely on interfacing with Indico over its HTTP API.

## Useful links
- https://docs.getindico.io/en/stable/http-api/access/
- https://docs.getindico.io/en/stable/http-api/exporters/event/
- https://talk.getindico.io/t/is-http-api-only-for-exporting-data/1907/

## Setup

My instructions assume the Indico Global instance, but any Indico instance with API access enabled should work. The Indico URL can be set in the config file.

1. Copy `config-template.yaml` to `config.yaml` and fill out the configuration with details of your Indico event ID and timezone. The timezone can probably be set to anything, regardless of where you are personally located (every timestamp in the code is timezone-aware) but I never tested this. Best to be safe and use your own location (assuming you are at the conference).
2. Create an Indico API token at https://indico.global/user/tokens/. Give it at least "Classic API (read-only)" scope access, but more scopes might be needed. Put the token in the config file. Never share this token!

## slack-announce-bot

Read the conference timetable from Indico and then post session and talk announcements in Slack using an incoming webhook.

Specific to our mode of running the conference, each venue (room) has its own Slack channel for questions and discussion. This script is designed to select one room and only announce the sessions and talks happening in that room in one specific Slack channel for as long as it's running. Multiple instances of the script running at once are used to cover the multiple rooms.

Setup:
1. Create Slack webhooks following the instructions from https://api.slack.com/messaging/webhooks. For each channel, fill its webhook URL into the config file.
2. Make sure you also have a mapping from Indico event "rooms" to the Slack channel names in the config file.

## protect-material

Scan the conference for presentation material (slides) and protect any material that is currently public. Protected material is configured to be accessible to conference registrants only.

Using this script requires your Indico API token to have both the "Everything (all methods)" and "Everything (only GET)" scope access as well as the other scope stated above.
