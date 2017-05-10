from django import template
from django.template import Context, Template

register = template.Library()


@register.simple_tag(takes_context=False)
def bootstrap_info_icon(text):
    """ Generate (i) icon with a tooltip """
    template = Template(
        """<span data-toggle="tooltip" title="{{ text }}" class="glyphicon glyphicon-info-sign"></span>"""
    )
    return template.render(Context({"text": text}))
