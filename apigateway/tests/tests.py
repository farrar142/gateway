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
