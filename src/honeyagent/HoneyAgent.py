import os
import sys
import errno
import base64
import requests
import tempfile
import logging

log = logging.getLogger("Thug")

try:
    import configparser as ConfigParser
except ImportError:
    import ConfigParser

try:
    from io import StringIO
except ImportError:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO


class HoneyAgent(object):
    def __init__(self):
        self.enabled = True
        self.opts    = dict()

        self.__init_config()

    def __init_config(self):
        config = ConfigParser.ConfigParser()

        conf_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'honeyagent.conf')
        if not os.path.isfile(conf_file):
            self.enabled = False
            return

        config.read(conf_file)

        for option in config.options('HoneyAgent'):
            self.opts[option] = config.get('HoneyAgent', option)

    def save_report(self, response, basedir, md5):
        log_dir = os.path.join(basedir, 'analysis', 'honeyagent')

        try:
            os.makedirs(log_dir)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise

        log_file = os.path.join(log_dir, '%s' % (md5, ))
        with open(log_file, 'w') as fd:
            fd.write(response.text)

    def save_dropped(self, response, basedir, md5):
        log_dir = os.path.join(basedir, 'analysis', 'honeyagent', 'dropped')

        try:
            os.makedirs(log_dir)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise

        data = response.json()
        try:
            files = data["result"]["files"]
        except:
            return

        for filename in files.keys():
            drop = os.path.join(log_dir, os.path.basename(filename))
            with open(drop, 'wb') as fd:
                data = base64.b64decode(files[filename])
                log.ThugLogging.log_file(data)
                log.warning("[HoneyAgent] Sample %s dropped sample %s" % (md5, os.path.basename(filename), ))
                fd.write(data)

    def submit(self, data, md5, params):
        sample = os.path.join(tempfile.gettempdir(), md5)

        with open(sample, "wb") as fd:
            fd.write(data)
       
        files    = {'file'  : (md5, open(sample, "rb"))}
        response = requests.post(self.opts["scanurl"], files = files, params = params)
        
        if response.ok:
            log.warning("[HoneyAgent] Sample %s submitted" % (md5, ))

        os.remove(sample)
        return response

    def analyze(self, data, md5, basedir, params):
        if not self.enabled:
            return

        if not log.ThugOpts.honeyagent:
            return

        if params is None:
            params = dict()

        response = self.submit(data, md5, params)
        self.save_report(response, basedir, md5)
        self.save_dropped(response, basedir, md5)
