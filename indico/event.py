import requests

from .utilities import convert_all_timestamps

class Event():
  """Interface to an Indico event via the HTTP API. See documentation at
  https://docs.getindico.io/en/stable/http-api/access/ and in particular,
  everything useful for events is (briefly) demonstrated at
  https://docs.getindico.io/en/stable/http-api/exporters/event/
  """

  def __init__(self, event_id: int, api_token: str, instance_url: str = 'https://indico.global', timezone: str = None):
    """Constructor.

      event_id: Indico event ID.
      api_token: Your Indico account API token from https://indico.global/user/tokens/.
        Counterintuitively, the token must have what is currently labelled the
        "Classic API" scope access at read-only level.
      instance_url: (optional) Indico instance, default is Indico Global.
      timezone: (optional) Timezone to assume for all queries (input and output).
        Defaults to 'Europe/Zurich'.
    """

    self.api_token = api_token
    self.event_id = event_id
    self.instance_url = instance_url
    self.export_params = {
      'occ': 'yes', # include "occurences" list in case this is useful
      'nocache': 'yes', # Sorry Indico, but we always want the latest data
    }
    if timezone:
      self.export_params['tz'] = timezone
    self.auth_headers = {'Authorization': 'Bearer ' + self.api_token}

  def _export_get(self, endpoint: str, params: dict = {}):
    """Make a GET request to the "export" API.
    eg, https://indico.global/export/event/xxxxx.xxxxx?x=y
    """
    api_url = '/'.join(elem.strip('/') for elem in [self.instance_url, endpoint, f'{self.event_id}.json'])
    api_params = self.export_params | params
    r = requests.get(api_url, params = api_params, headers = self.auth_headers)
    r.raise_for_status()
    return r

  def _api_get(self, endpoint: str):
    """Make a GET request to the "api" API (don't ask me why they called it that).
    eg, https://indico.global/event/xxxxx/api/xxxxx
    """
    api_url = '/'.join(elem.strip('/') for elem in [self.instance_url, f'/event/{self.event_id}', endpoint])
    r = requests.get(api_url, headers = self.auth_headers)
    r.raise_for_status()
    return r

  def _manage_post(self, endpoint: str, payload: [dict, str]):
    """Make a POST request to the undocumented "manage" internal API.
    This API comes with no guarantees on stability or backwards compatibility.
    Some endpoints expect form-encoded data (use a dict payload), some might
    expect JSON data (use a string payload).
    """
    api_url = '/'.join(elem.strip('/') for elem in [self.instance_url, f'/event/{self.event_id}', endpoint])
    r = requests.post(api_url, data = payload, headers = self.auth_headers)
    r.raise_for_status()
    return r

  def get_event(self):
    endpoint = '/export/event' # scope = read:legacy_api
    r = self._export_get(endpoint)
    data = r.json()['results'][0]
    convert_all_timestamps(data)
    return data

  def get_sessions(self):
    endpoint = '/export/event' # scope = read:legacy_api
    params = {'detail': 'sessions'}
    r = self._export_get(endpoint, params)
    data = r.json()['results'][0]['sessions']
    #TODO: The 'contributions' key exists and contains contributions that don't belong to a session
    convert_all_timestamps(data)
    # Sort by start time then ID, which matches the style in Indico Web
    data.sort(key = lambda s: (s['startDate'], s['id']))
    for sess in data:
      sess['contributions'].sort(key = lambda c: (c['startDate'], c['id']))
    return data

  def get_contributions(self): # scope = read:legacy_api
    endpoint = '/export/event'
    params = {'detail': 'contributions'}
    r = self._export_get(endpoint, params)
    data = r.json()['results'][0]['contributions']
    convert_all_timestamps(data)
    # Sort by start time then ID
    data.sort(key = lambda s: (s['startDate'], s['id']))
    return data

  def get_timetable(self): # scope = read:legacy_api
    endpoint = '/export/timetable'
    params = {'detail': 'contributions'}
    r = self._export_get(endpoint, params)
    data = r.json()['results'][str(self.event_id)]
    convert_all_timestamps(data)
    return data

  def get_registration_forms(self):
    endpoint = '/api/registration-forms' # scope = read:everything
    r = self._api_get(endpoint)
    return r.json()

  def update_attachment(self, attachment: dict, changes: dict):
    """Modify the properties of an attachment. This assumes the endpoint wants
    form-encoded data and that we can safely use the download URL to get the
    contribution db_id and the folder id.
    """
    # Extract the part of the URL that has the contribution ID, folder ID, and attachment ID
    url_seg = attachment['download_url'].split('/')
    del url_seg[-1] # Filename
    while url_seg[0] != 'contributions':
      del url_seg[0]
    endpoint = f'/manage/{"/".join(url_seg)}' # scope = full:everything
    payload = {
      # Assume the default folder. This is the only field that MUST be present
      'folder': '__None',
    }
    return self._manage_post(endpoint, payload | changes)
