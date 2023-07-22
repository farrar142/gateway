# import requests_unixsocket
import json
import requests
from typing import Any, Callable, Self, Type

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.html import format_html
from django.urls import reverse_lazy

from base.caches import UseSingleCache
from base.wrappers import MockRequest

from .nodes import ChildNode, LoadBalancer
from .plugins import PluginChoices, PluginMixin


class User(AbstractUser):
    nickname = models.CharField(max_length=150)

    @property
    def user_id(self):
        return self.pk

    def __str__(self):
        return self.username

    def __getitem__(self, key: str, default=None):
        return getattr(self, key, default)

    def get(self, key: str, default=None):
        return self.__getitem__(key, default)


class ApiType(models.TextChoices):
    NORMAL = "일반"
    ADMIN = "관리자"


# 로드밸런싱을 수행 할 실제 모델
class Upstream(LoadBalancer):
    alias = models.CharField(max_length=64, default="", unique=True)
    targets: models.Manager["Target"]
    api_set: models.Manager["Api"]

    # 어드민 페이지 관리를 위한 필드들
    @property
    def total_targets(self):
        return self.targets.count() or 1

    total_targets.fget.short_description = "Total Node Count"

    @property
    def total_apis(self):
        return self.api_set.count()

    total_apis.fget.short_description = "Total API Route Count"

    @property
    def total_weight(self):
        aggregate = self.targets.aggregate(total_weight=models.Sum(models.F("weight")))[
            "total_weight"
        ]
        # raise
        aggregate = aggregate or 0
        return aggregate + self.weight

    total_weight.fget.short_description = "Total Weight"

    def to_string(self):
        return self.host

    def __str__(self):
        return f"{self.alias}"


# 분산 부하를 수행할 노드들의 실제 모델
class Target(ChildNode):
    upstream = models.ForeignKey(
        Upstream, on_delete=models.CASCADE, related_name="targets"
    )
    upstream_id: int

    def toggle_button(self):
        text = "Activate" if not self.enabled else "Deactivate"
        return format_html(
            '<a href="{}" class="link">{}</a>',
            reverse_lazy("admin:admin_toggle_enabled", args=[self.pk]),
            text,
        )

    def to_string(self):
        return self.host

    def __str__(self):
        str(self.upstream.alias)
        return f"{self.scheme}/{self.host} - {self.weight}"


# api 라우팅을 하는 모델
class Api(PluginMixin, models.Model):
    cache: UseSingleCache[Type[Self]] = UseSingleCache(0, "api")

    name = models.CharField(max_length=128)
    request_path = models.CharField(max_length=255)  # 요청받을 주소 /users
    wrapped_path = models.CharField(max_length=255)  # 라우팅할 주소 /auth/users
    upstream = models.ForeignKey(
        Upstream, on_delete=models.CASCADE, related_name="api_set"
    )

    method_map: dict[str, Callable[..., requests.Response]] = {
        "get": requests.get,
        "post": requests.post,
        "put": requests.put,
        "patch": requests.patch,
        "delete": requests.delete,
    }

    def get_trailing_path(self, request: MockRequest):
        """
        업스트림의 주소와, request_path를 제외한 나머지
        ex) https://test.com/users/1/memberships
        request.get_full_path() = /users/1/memberships
        .removeprefix(self.request_path) => /1/memberships
        """
        return request.get_full_path().removeprefix(self.request_path)

    def get_method(self, request: MockRequest):
        method = request.method or "get"
        return method.lower()

    # 요청자의 헤더중 필요한 헤더만 뽑아 뒷단의 서비스에게 넘겨줌
    def process_headers(self, request: MockRequest):
        headers = {}
        # 게이트웨이에서 뒷단의 서비스로 넘어 갈 시 요청된 주소가 게이트웨이의 주소로 바뀌는 것을 해결
        foward = request.headers.get("X-Forwarded-For", None)
        if foward != None:
            headers["X-Forwarded-For"] = foward
        host = request.headers.get("Host", None)
        if host != None:
            headers["Host"] = host
        authorization = request.META.get("HTTP_AUTHORIZATION")
        if authorization != None:
            headers["Authorization"] = authorization
        if request.content_type and request.content_type.lower() == "application/json":
            headers["Content-Type"] = request.content_type
        return headers

    # drf에서 file안의 객체들이 data로도 카피되는 것을 다시 되돌려줌
    def process_data(self, request: MockRequest):
        if request.FILES is not None and isinstance(request.FILES, dict):
            for k, v in request.FILES.items():
                if request.data.get(k, False):
                    request.data.pop(k)
        if request.content_type and request.content_type.lower() == "application/json":
            data = json.dumps(request.data)
        else:
            data = request.data
        return data

    # 디버깅용으로 에러가 발생 시 에러 내용을 출력해줌
    def show_errors(self, resp: requests.Response):
        if resp.status_code in [400, 404, 409]:
            try:
                print(resp.json())
            except:
                pass

    # 리퀘스트 객체들을 수정하여 실제 요청을 보내고 받음
    def send_request(self, request: MockRequest):
        trailing_path = self.get_trailing_path(request)
        method = self.get_method(request)
        headers = self.process_headers(request)
        data = self.process_data(request)
        resp = self.upstream.send_request(
            self, trailing_path, method, headers, data, request.FILES
        )
        self.show_errors(resp)
        return resp

    # api가 수정 될 시 업스트림에 연결된 모든 api캐시들을 퍼지
    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        self.cache.purge_by_regex(path="*", upstream=self.upstream.pk)
        return instance

    # api가 삭제 될 시 업스트림에 연결된 모든 api캐시들을 퍼지
    def delete(self, *args, **kwargs) -> tuple[int, dict[str, int]]:
        self.cache.purge_by_regex(path="*", upstream=self.upstream.pk)
        deleted = super().delete(*args, **kwargs)
        return deleted

    def __unicode__(self):
        return self.name

    def __str__(self):
        return f"{self.name}"

    def get(self, __name: str):
        return self.__getattribute__(__name)

    def __enter__(self):
        # con = self.upstream.incr_conn()
        # print(f"{self.upstream} conn count", con)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # con = self.upstream.decr_conn()
        return


class DefaultApi(Api):
    class Meta:
        proxy = True

    class ApiManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(plugin=PluginChoices.NO_AUTH)

    objects = ApiManager()


class KeyApi(Api):
    class Meta:
        proxy = True

    class ApiManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(plugin=PluginChoices.KEY_AUTH)

    objects = ApiManager()


class BasicApi(Api):
    class Meta:
        proxy = True

    class ApiManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(plugin=PluginChoices.BASIC_AUTH)

    objects = ApiManager()


class AdminApi(Api):
    class Meta:
        proxy = True

    class ApiManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(plugin=PluginChoices.ADMIN_ONLY)

    objects = ApiManager()


class ETCApi(Api):
    class Meta:
        proxy = True

    class ApiManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(plugin__gt=PluginChoices.ADMIN_ONLY)

    objects = ApiManager()
