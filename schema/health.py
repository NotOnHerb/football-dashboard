"""The build sections whose failure fails the daily run (check_health.py) and turns health.json's ok off (api_export.py)."""

CORE_SECTIONS = ['schedule', 'injuries', 'depth', 'weekly', 'odds']
