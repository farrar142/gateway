import asyncio

from django.http import HttpResponse
from base.caches import cache
from django.core.handlers.wsgi import WSGIRequest
import logging
from rest_framework import exceptions
from django.conf import settings

DDOSReponse = HttpResponse("Too many Requests")
DDOSReponse.status_code = 429
MAX_REQUESTS_PER_SECONDS = 25


def get_origin(request: WSGIRequest):
    origin = request.META.get("REMOTE_ADDR", "")
    if not origin:
        origin = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return origin


def blocker(origin: str):
    if not origin:
        return
    block_key = f"BLOCK:ORIGIN:{origin}"
    if cache.get(block_key, False):
        return DDOSReponse
    return


def req_counter(origin: str):
    cache_key = f"REQ:ORIGIN:{origin}"
    req: int = cache.get_or_set(cache_key, 0, 1)  # type: ignore
    try:
        req: int = cache.incr(cache_key, 1)
    except:
        pass
    return req


def handle_block(origin: str, req: int):
    if MAX_REQUESTS_PER_SECONDS <= req:
        block_key = f"BLOCK:ORIGIN:{origin}"
        cache.add(block_key, True, 20)
        return DDOSReponse
    return req


def handle_request(request: WSGIRequest):
    origin = get_origin(request)
    if request.method == "GET":
        return
    white_list = getattr(settings, "DDOS_WHITELIST", ["192.168.0.1"])
    if origin in white_list:
        return
    response = blocker(origin)
    if response:
        return response
    req = req_counter(origin)
    result = handle_block(origin, req)
    if isinstance(result, int):
        return
    return result


def DDOSBlocker(get_response):
    logger = logging.getLogger("django")

    logger.setLevel(logging.INFO)
    if asyncio.iscoroutinefunction(get_response):

        async def async_middleware(request):
            response = handle_request(request)
            if response:
                return response
            response = await get_response(request)
            return response

        function = async_middleware
    else:

        def middleware(request):
            response = handle_request(request)
            if response:
                return response
            response = get_response(request)
            return response

        function = middleware
    return function
