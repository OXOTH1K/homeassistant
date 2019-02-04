# -*- coding: utf-8 -*-
import requests
import json
from lxml import etree
from .UPNP_Device.discover import discover as _discover
from .UPNP_Device.xmlns import strip_xmlns
from ..config import Config


def discover(config=None, log_level=None, timeout=5):
    if isinstance(config, dict):
        config = Config(**config)

    if config is None:
        upnp_locations = None
        search_ips = ()

    else:
        upnp_locations = config.upnp_locations
        if not upnp_locations:
            upnp_locations = None
            config.upnp_locations = None

        search_ips = (config.host,)

    if upnp_locations is None:
        found = []
        for ip, locations in _discover(timeout, log_level, search_ips=search_ips):
            if search_ips:
                config.upnp_locations = locations
                found += [config]
            else:
                location = locations[0]

                response = requests.get(location)
                root = etree.fromstring(response.content)

                root = strip_xmlns(root)

                device = root.find('device')
                mfgr = device.find('manufacturer').text

                if mfgr == 'Samsung Electronics':
                    try:
                        response = requests.get(
                            'http://{0}:8001/api/v2/'.format(ip),
                            timeout=3
                        )
                        is_support = (
                            json.loads(response.content)['device']['isSupport']
                        )
                        token_support = json.loads(is_support)['TokenAuthSupport']

                        if token_support:
                            port = 8002
                            method = 'websocket'

                        else:
                            raise ValueError


                    except (requests.HTTPError, requests.exceptions.ConnectTimeout):
                        port = 55000
                        method = 'legacy'

                    except (ValueError, KeyError):
                        port = 8001
                        method = 'websocket'

                    host = ip
                    config = Config(
                        host=host,
                        method=method,
                        port=port,
                        upnp_locations=locations
                    )

                found += [config]
    else:
        found = [config]

    if search_ips and config.upnp_locations is None:
        config.upnp_locations = []

    return found
