# -*- coding: utf-8 -*-
import threading
import base64
import requests
import json
import six
import sys
from .utils import LogIt, LogItWithReturn

PY3 = sys.version_info[0] > 2

_instances = {}


# noinspection PyPep8Naming
class Singleton(type):

    def __call__(
        cls,
        parent,
        title=None,
        name=None,
        appId=None,
        id=None,
        **kwargs
    ):
        if cls not in _instances:
            _instances[cls] = {}

        instances = _instances[cls]
        if parent not in instances:
            instances[parent] = {}

        instances = instances[parent]

        if cls == Application:
            if (name, appId) not in instances:
                instance = (
                    super(Singleton, cls).__call__(
                        parent,
                        name,
                        appId,
                        id,
                        **kwargs
                    )
                )
                instances[(name, appId)] = instance
            else:
                instance = instances[(name, appId)]
                instance.update(**kwargs)

        elif cls == AppData:
            if (title, id) not in instances:
                instance = (
                    super(Singleton, cls).__call__(
                        parent,
                        title,
                        id,
                        appId,
                        **kwargs
                    )
                )
                instances[(title, id)] = instance
            else:
                instance = instances[(title, id)]
                instance.update(**kwargs)

        else:
            if (parent, title) not in instances:
                instance = (
                    super(Singleton, cls).__call__(
                        parent,
                        title,
                        **kwargs
                    )
                )
                instances[(parent, title)] = instance
            else:
                instance = instances[(parent, title)]
                instance.update(**kwargs)

        return instance


# noinspection PyUnusedLocal,PyDeprecation,PyPep8Naming
@six.add_metaclass(Singleton)
class Application(object):

    @LogIt
    def __init__(
        self,
        remote,
        name=None,
        appId=None,
        id=None,
        isLock=None,
        is_lock=None,
        appType=None,
        app_type=None,
        position=None,
        launcherType=None,
        action_type=None,
        mbrIndex=None,
        accelerators=None,
        sourceTypeNum=None,
        icon=None,
        mbrSource=None,
        **kwargs
    ):
        self._remote = remote
        self._is_lock = isLock
        self.name = name
        self.app_type = app_type
        self.position = position
        self.app_id = appId
        self.launcher_type = launcherType
        self.mbr_index = mbrIndex
        if accelerators is not None:
            self._accelerators = accelerators
        else:
            self._accelerators = []
        self.source_type_num = sourceTypeNum
        self._icon = icon
        self.id = id
        self.mbr_source = mbrSource

        self._kwargs = kwargs
        self._categories = {}

    def __getitem__(self, item):
        if item in self._kwargs:
            return self._kwargs[item]

        raise KeyError(item)

    def update(
        self,
        isLock=None,
        is_lock=None,
        appType=None,
        app_type=None,
        position=None,
        launcherType=None,
        action_type=None,
        mbrIndex=None,
        accelerators=None,
        sourceTypeNum=None,
        icon=None,
        mbrSource=None,
        **kwargs
    ):
        self._is_lock = isLock
        self.app_type = app_type
        self.position = position
        self.launcher_type = launcherType
        self.mbr_index = mbrIndex
        self.source_type_num = sourceTypeNum
        self._icon = icon
        self.mbr_source = mbrSource
        self._kwargs.update(kwargs)
        if accelerators is not None:
            self._accelerators = accelerators
        else:
            self._accelerators = []

    @property
    @LogItWithReturn
    def action_type(self):
        if self.app_type == 2:
            return 'DEEP_LINK'
        else:
            return 'NATIVE_LAUNCH'

    @property
    @LogItWithReturn
    def version(self):
        url = 'http://{0}:8001/api/v2/applications/{1}'.format(
            self._remote.config.host,
            self.app_id
        )

        response = requests.get(url)
        try:
            response = response.json()
        except ValueError:
            return 'Unknown'

        if 'version' not in response:
            return 'Unknown'

        return response['version']

    @property
    @LogItWithReturn
    def is_visible(self):
        url = 'http://{0}:8001/api/v2/applications/{1}'.format(
            self._remote.config.host,
            self.app_id
        )

        response = requests.get(url)
        try:
            response = response.json()
        except ValueError:
            return None

        if 'visible' not in response:
            return None

        return response['visible']

    @property
    @LogItWithReturn
    def is_running(self):
        url = 'http://{0}:8001/api/v2/applications/{1}'.format(
            self._remote.config.host,
            self.app_id
        )

        response = requests.get(url)
        try:
            response = response.json()
        except ValueError:
            return None

        if 'running' not in response:
            return None

        return response['running']

    def get_category(self, title):
        for group in self:
            if title == group.title:
                return group

    @LogIt
    def run(self, meta_tag=None):
        params = dict(
            event='ed.apps.launch',
            to='host',
            data=dict(
                appId=self.app_id,
                action_type=self.action_type
            )
        )

        if meta_tag is not None:
            params['data']['metaTag'] = meta_tag

        self._remote.send('ms.channel.emit', **params)

    @property
    @LogItWithReturn
    def is_lock(self):
        return bool(self._is_lock)

    def __iter__(self):
        accelerators = dict(
            (accelerator['title'], accelerator)
            for accelerator in self._accelerators
            if accelerator['title'] is not None
        )
        for accelerator_name in sorted(list(accelerators.keys())):
            yield Accelerator(self, **accelerators[accelerator_name])

    @property
    @LogIt
    def icon(self):
        if self._icon:
            params = dict(
                event="ed.apps.icon",
                to="host",
                data=dict(iconPath=self._icon)

            )

            icon = [None]
            event = threading.Event()

            @LogIt
            def app_icon_callback(data):
                data = data['imageBase64']
                if data is not None:
                    if PY3:
                        data = base64.decodebytes(data)
                    else:
                        data = base64.decodestring(data)
                icon[0] = data
                event.set()

            self._remote.register_receive_callback(
                app_icon_callback,
                'event',
                'ed.apps.icon'
            )

            self._remote.send("ms.channel.emit", **params)

            event.wait(3.0)
            self._remote.unregister_receive_callback(
                app_icon_callback,
                'event',
                'ed.apps.icon'
            )
            return icon[0]


# noinspection PyPep8Naming
@six.add_metaclass(Singleton)
class Accelerator(object):

    @LogIt
    def __init__(
        self,
        application,
        title,
        appDatas,
        **kwargs
    ):
        self.application = application
        self.title = title
        self._app_datas = appDatas
        self._kwargs = kwargs

    def __getitem__(self, item):
        if item in self._kwargs:
            return self._kwargs[item]

        raise KeyError(item)

    def update(self, appDatas, **kwargs):
        self._app_datas = appDatas
        self._kwargs.update(kwargs)

    def get_content(self, title):
        for content in self:
            if title in (content.title, content.id):
                return content

    def __iter__(self):
        content = dict(
            (app_data['title'], app_data) for app_data in self._app_datas
            if app_data['title'] is not None
        )

        for content_name in sorted(list(content.keys())):
            yield AppData(self.application, **content[content_name])


# noinspection PyProtectedMember,PyDeprecation,PyPep8Naming
@six.add_metaclass(Singleton)
class AppData(object):

    @LogIt
    def __init__(
        self,
        application,
        title=None,
        id=None,
        appId=None,
        isPlayable=None,
        subtitle=None,
        appType=None,
        mbrIndex=None,
        liveLauncherType=None,
        action_play_url=None,
        serviceId=None,
        launcherType=None,
        sourceTypeNum=None,
        action_type=None,
        subtitle2=None,
        display_from=None,
        display_until=None,
        mbrSource=0,
        subtitle3=None,
        icon=None,
        **kwargs
    ):

        self.application = application
        self._is_playable = isPlayable
        self.subtitle = subtitle
        self.app_type = appType
        self.title = title
        self.mbr_index = mbrIndex
        self.live_launcher_type = liveLauncherType
        self.action_play_url = action_play_url
        self.service_id = serviceId
        self.launcher_type = launcherType
        self.source_type_num = sourceTypeNum
        self.action_type = action_type
        self.app_id = appId
        self.subtitle2 = subtitle2
        self.display_from = display_from
        self.display_until = display_until
        self.mbr_source = mbrSource
        self.id = id
        self.subtitle3 = subtitle3
        self._icon = icon
        self._kwargs = kwargs

    def update(
        self,
        isPlayable=None,
        subtitle=None,
        appType=None,
        mbrIndex=None,
        liveLauncherType=None,
        action_play_url=None,
        serviceId=None,
        launcherType=None,
        sourceTypeNum=None,
        action_type=None,
        subtitle2=None,
        display_from=None,
        display_until=None,
        mbrSource=0,
        subtitle3=None,
        icon=None,
        **kwargs
    ):
        self._is_playable = isPlayable
        self.subtitle = subtitle
        self.app_type = appType
        self.mbr_index = mbrIndex
        self.live_launcher_type = liveLauncherType
        self.action_play_url = action_play_url
        self.service_id = serviceId
        self.launcher_type = launcherType
        self.source_type_num = sourceTypeNum
        self.action_type = action_type
        self.subtitle2 = subtitle2
        self.display_from = display_from
        self.display_until = display_until
        self.mbr_source = mbrSource
        self.subtitle3 = subtitle3
        self._icon = icon
        self._kwargs.update(kwargs)

    @property
    @LogItWithReturn
    def is_playable(self):
        return bool(self._is_playable)

    def __getitem__(self, item):
        if item in self._kwargs:
            return self._kwargs[item]

        raise KeyError(item)

    @LogIt
    def run(self):
        if self.is_playable:

            if self.action_play_url is None:
                meta_tag = self.app_id
            elif self.action_play_url:
                if isinstance(self.action_play_url, dict):
                    meta_tag = json.dumps(self.action_play_url)
                else:
                    meta_tag = self.action_play_url
            else:
                meta_tag = None

            self.application.run(meta_tag)

    @property
    def icon(self):
        if self._icon:
            params = dict(
                event="ed.apps.icon",
                to="host",
                data=dict(iconPath=self._icon)

            )
            icon = [None]
            event = threading.Event()

            @LogIt
            def content_icon_callback(data):
                data = data['imageBase64']
                if data is not None:
                    if PY3:
                        data = base64.decodebytes(data)
                    else:
                        data = base64.decodestring(data)

                icon[0] = data
                event.set()

            self.application._remote.register_receive_callback(
                content_icon_callback,
                'event',
                'ed.apps.icon'
            )

            self.application._remote.send("ms.channel.emit", **params)

            event.wait(3.0)
            self.application._remote.unregister_receive_callback(
                content_icon_callback,
                'event',
                'ed.apps.icon'
            )
            return icon[0]
