activate_this = '/home/sparkplug/venv/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))

from pyramid.paster import get_app, setup_logging
ini_path = '/home/sparkplug/sparkplug-boxes/development.ini'
setup_logging(ini_path)
application = get_app(ini_path, 'main')