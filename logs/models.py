from django.db import models

from base.wrappers import MockRequest


class Log(models.Model):
    user_id = models.IntegerField(null=True)
    ip_address = models.GenericIPAddressField(null=True)
    path_info = models.TextField()
    method = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True, null=False, help_text="생성 날짜")

    def __str__(self):
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S'):{20}} {self.method:{7}} {str(self.user_id):{6}} {self.ip_address or '':{20}} {self.path_info}"
