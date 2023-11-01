import os
from uuid import uuid4
from dotenv import load_dotenv

from django.conf import settings
from rest_framework import status
from base.test import TestCase
from apigateway.models import Api, Upstream, Target, User
from base.caches import UseSingleCache, cache

load_dotenv()
AUTH_USER = os.getenv("ADMIN_USER", "")
AUTH_PASSWORD = os.getenv("ADMIN_PASSWORD")
# Create your tests here.
SCHEME = "https"


class TestApiGateway(TestCase):
    auth: Api
    def test_query_param(self):
        upstream = Upstream.objects.create(alias='SWAGGER',scheme="https",host="auth.honeycombpizza.link")
        upstream.api_set.create(
            name="swagger",
            request_path='/swagger/users/',
            wrapped_path='/swagger/users/'
        )
        print("get start ===========")
        resp = self.client.get('/swagger/users/?format=openapi')
        from logs.models import Log
        print(Log.objects.all())