from datetime import datetime

from django.conf.urls import include
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import re_path
from django.utils.timezone import get_current_timezone
from django.views.decorators.http import last_modified
from django.views.generic.base import TemplateView
from django.views.i18n import JavaScriptCatalog

last_modified_date = datetime.now(tz=get_current_timezone())

urlpatterns = i18n_patterns(
    re_path(r'^$', TemplateView.as_view(template_name='index.html'), name='index'),
    re_path(r'^admin/', include(admin.site.urls)),
    re_path(r'^i18n/', include('django.conf.urls.i18n')),
    re_path(r'^jsi18n/$', last_modified(lambda req, **kw: last_modified_date)(JavaScriptCatalog.as_view()), name='website.javascript_catalog'),
)
