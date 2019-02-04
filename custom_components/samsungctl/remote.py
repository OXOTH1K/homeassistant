# -*- coding: utf-8 -*-

import six
from . import exceptions
from .remote_legacy import RemoteLegacy
from .remote_websocket import RemoteWebsocket
from .config import Config
from .key_mappings import KEYS
from .upnp import UPNPTV
from .upnp.discover import discover

try:
    from .remote_encrypted import RemoteEncrypted
except ImportError:
    RemoteEncrypted = None


class KeyWrapper(object):
    def __init__(self, remote, key):
        self.remote = remote
        self.key = key

    def __call__(self):
        self.key(self.remote)


class RemoteMeta(type):

    def __call__(cls, conf):

        if isinstance(conf, dict):
            conf = Config(**conf)

        if conf.method == "legacy":
            remote = RemoteLegacy
        elif conf.method == "websocket":
            remote = RemoteWebsocket
        elif conf.method == "encrypted":
            if RemoteEncrypted is None:
                raise RuntimeError(
                    'Python 2 is not currently supported '
                    'for H and J model year TV\'s'
                )

            remote = RemoteEncrypted
        else:
            raise exceptions.ConfigUnknownMethod()


        class RemoteWrapper(remote, UPNPTV):

            def __init__(self, config):
                for name, key in KEYS.items():
                    self.__dict__[name] = KeyWrapper(self, key)

                remote.__init__(self, config)

                if config.upnp_locations is not None:
                    discover(config)

                if config.upnp_locations:
                    UPNPTV.__init__(
                        self,
                        config.host,
                        config.upnp_locations,
                        self
                    )

                if config.path:
                    config.save()

                self.open()

        return RemoteWrapper(conf)


@six.add_metaclass(RemoteMeta)
class Remote(object):

    def __init__(self, config):
        self.config = config

