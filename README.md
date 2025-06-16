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

## protect-material

Scan the conference for presentation material (slides) and protect any material that is currently public. Protected material is configured to be accessible to conference registrants only.
