from datetime import datetime
from zoneinfo import ZoneInfo

def make_datetime(indico_stamp: dict):
  """Convert an Indico API format timestamp to a Python Datetime.
  """
  dt = datetime.fromisoformat(f"{indico_stamp['date']}T{indico_stamp['time']}")
  dt = dt.replace(tzinfo=ZoneInfo(indico_stamp['tz']))
  return dt


def convert_all_timestamps(indico_data: dict):
  """Descend through an entire Indico API results structure and replace each
  Indico-format timestamp with a Python Datetime.
  """
  if isinstance(indico_data, dict):
    if 'startDate' in indico_data:
      indico_data['startDate'] = make_datetime(indico_data['startDate'])
    if 'endDate' in indico_data:
      indico_data['endDate'] = make_datetime(indico_data['endDate'])
    for obj in indico_data.values():
      convert_all_timestamps(obj)
  elif isinstance(indico_data, list):
    for obj in indico_data:
      convert_all_timestamps(obj)
  else:
    return
