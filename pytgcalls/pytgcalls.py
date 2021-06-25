import os
from time import time
from typing import Callable
from typing import Dict
from typing import List

from telethon import __version__
from telethon import TelegramClient, events
from telethon.sync import TelegramClient as SyncClient
from telethon.tl.types import ChannelForbidden
from telethon.tl.types import GroupCall
from telethon.tl.types import GroupCallDiscarded
from telethon.tl.types import InputGroupCall
from telethon.tl.types import MessageActionInviteToGroupCall
from telethon.tl.types import UpdateChannel
from telethon.tl.types import UpdateGroupCall
from telethon.tl.types import UpdateNewChannelMessage

from .methods import Methods


class PyTgCalls(Methods):
    def __init__(
        self,
        api_id: int = None,
        api_hash:str = None,
        session= None,
        port: int = 24859,
        log_mode: int = 0,
        flood_wait_cache: int = 120,
    ):  
        app = TelegramClient(session,
                             api_id=api_id, 
                             api_hash=api_hash)
        SyncApp = TelegramClient(session,
                             api_id=api_id, 
                             api_hash=api_hash)
        self._app = app
        self._syncapp = SyncApp
        self._app_core = None
        self._sio = None
        self._host = '127.0.0.1'
        self._port = port
        self._init_js_core = False
        self._on_event_update: Dict[str, list] = {
            'EVENT_UPDATE_HANDLER': [],
            'STREAM_END_HANDLER': [],
            'CUSTOM_API_HANDLER': [],
            'GROUP_CALL_HANDLER': [],
            'KICK_HANDLER': [],
            'CLOSED_HANDLER': [],
        }
        self._my_id = 0
        self.is_running = False
        self._calls: List[int] = []
        self._active_calls: Dict[int, str] = {}
        self._async_processes: Dict[str, Dict] = {}
        self._session_id = self._generate_session_id(20)
        self._log_mode = log_mode
        self._cache_user_peer: Dict[int, Dict] = {}
        self._cache_full_chat: Dict[int, Dict] = {}
        self._cache_local_peer = None
        self._flood_wait_cache = flood_wait_cache
        super().__init__(self)

    @staticmethod
    def verbose_mode():
        return 1

    @property
    def ultra_verbose_mode(self):
        return 2

    @staticmethod
    def get_version(package_check):
        result_cmd = os.popen(f'{package_check} -v').read()
        result_cmd = result_cmd.replace('v', '')
        if len(result_cmd) == 0:
            return {
                'version_int': 0,
                'version': '0',
            }
        return {
            'version_int': int(result_cmd.split('.')[0]),
            'version': result_cmd,
        }

    def run(self, before_start_callable: Callable = None):
        if self._app is not None:
            node_result = self.get_version('node')
            if node_result['version_int'] == 0:
                raise Exception('Please install node (15.+)')
            if node_result['version_int'] < 15:
                raise Exception(
                    'Needed node 15.+, '
                    'actually installed is '
                    f"{node_result['version']}",
                )
            try:
                # noinspection PyBroadException
                @self._app.on(events.Raw())
                async def on_close(update):
                    if isinstance(update, UpdateGroupCall):
                        if isinstance(update.call, GroupCallDiscarded):
                            chat_id = int(f'-100{update.chat_id}')
                            self._cache_full_chat[chat_id] = {
                                'last_update': int(time()),
                                'full_chat': None,
                            }
                        if isinstance(update.call, GroupCall):
                            input_group_call = InputGroupCall(
                                access_hash=update.call.access_hash,
                                id=update.call.id,
                            )
                            chat_id = int(f'-100{update.chat_id}')
                            self._cache_full_chat[chat_id] = {
                                'last_update': int(time()),
                                'full_chat': input_group_call,
                            }
                    if isinstance(update, UpdateChannel):
                        chat_id = int(f'-100{update.channel_id}')
                    if isinstance(
                            update,
                            UpdateGroupCall,
                    ):
                        if isinstance(
                                update.call,
                                GroupCallDiscarded,
                        ):
                            chat_id = int(f'-100{update.chat_id}')
                            for event in self._on_event_update[
                                'CLOSED_HANDLER'
                            ]:
                                await event['callable'](
                                    chat_id,
                                )
                            # noinspection PyBroadException
                            try:
                                self.leave_group_call(
                                    chat_id,
                                    'closed_voice_chat',
                                )
                            except Exception:
                                pass
                            try:
                                del self._cache_user_peer[chat_id]
                            except Exception:
                                pass
                    if isinstance(
                            update,
                            UpdateNewChannelMessage,
                    ):
                        try:
                            if isinstance(
                                    update.message.action,
                                    MessageActionInviteToGroupCall,
                            ):
                                for event in self._on_event_update[
                                    'GROUP_CALL_HANDLER'
                                ]:
                                    await event['callable'](
                                        self._app, update.message,
                                    )
                        except Exception:
                            pass
                with self._syncapp as Temp:
                    self._my_id = Temp.get_me().id  # noqa
                    self._cache_local_peer = self._app.get_input_entity(
                    self._my_id,
                    )
                if before_start_callable is not None:
                    # noinspection PyBroadException
                    try:
                        result = before_start_callable(self._my_id)
                        if isinstance(result, bool):
                            if not result:
                                return
                    except Exception:
                        pass
                self._spawn_process(
                    self._run_js,
                    (
                        f'{__file__.replace("pytgcalls.py", "")}dist/index.js',
                        f'port={self._port} log_mode={self._log_mode}',
                    ),
                )
            except KeyboardInterrupt:
                pass
            self._start_web_app()
            self.is_running = True
        else:
            raise Exception('NEED_TELETHON_CLIENT')
        return self

    def _add_handler(self, type_event: str, func):
        self._on_event_update[type_event].append(func)
