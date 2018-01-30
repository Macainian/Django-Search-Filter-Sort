from django import template
from django.template import Context, Template

register = template.Library()


@register.simple_tag(takes_context=False)
def bootstrap_info_icon(text):
    """ Generate (i) icon with a tooltip """
    template = Template(
        """<i data-toggle="tooltip" title="{{ text }}" class="fas fa-info-circle no-right-margin"></i>"""
    )
    return template.render(Context({"text": text}))
