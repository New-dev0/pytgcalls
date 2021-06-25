import json

from aiohttp import web
from aiohttp.web_request import BaseRequest
from telethon.tl.functions.phone import LeaveGroupCallRequest


class LeaveVoiceCall:
    def __init__(self, pytgcalls):
        self.pytgcalls = pytgcalls

    # noinspection PyProtectedMember
    async def _leave_voice_call(self, request: BaseRequest):
        params = await request.json()
        result = {
            'result': 'OK',
        }
        if isinstance(params, str):
            params = json.loads(params)
        try:
            # noinspection PyBroadException
            chat_call = await self.pytgcalls._load_chat_call(
                int(params['chat_id']),
            )
            if chat_call is not None:
                # noinspection PyBroadException
                await self.pytgcalls._app(
                    LeaveGroupCallRequest(
                        call=chat_call,
                        source=0,
                    ),
                )
        except Exception as e:
            result = {
                'result': str(e),
            }
            pass
        return web.json_response(result)
