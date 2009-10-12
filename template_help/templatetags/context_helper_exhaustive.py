import types
from django import template
from django.template.defaultfilters import mark_safe, force_escape, pluralize
from django.forms import Form
from django.db.models import Model
from django.db.models.query import QuerySet
from django.core import urlresolvers
#TODO
#   - place keys provided by context processors in separate section
#   - if model, link to admin docs
#   - if form, list fields
#   - if container, key, nest new table
"""

From place detail:
c = Context(request, {
    'auto_brand_list': auto_brand_list,
    'content_object': p,
    'deal_list': deal_list,
    'drink_specials': drink_specials,
    'event_time_list': event_time_list,
    'map_address': map_address,
    'movie_list': movie_list,
    'num_events_in_past': p.get_event_time_count(past=True),
    'place': p,
    'placetypes': p.place_types.filter(user_nav__exact=True),
    'recurring_event_time_list': recurring_event_list,
    'related_link_list': p.related_links.all(),
    'restaurant': rest,
    'see_all': see_all,
    'teams': teams,
})


Context includes:
<table>
    <tr><td>auto_brand_list</td><td>list</td><td>(empty)</td></tr>
    <tr><td>content_object</td><td>Place></td><td>admin link</td></tr>
    <tr><td>map_address</td><td>str</td><td>escaped....[:100]</td></tr>
    ...
</table>
"""
#containers:
#    dict, list, set

MAX_DEPTH = 5

def _type_helper(o):
    if isinstance(o, Model):
        return "%s.%s" % o._meta.app_label, o._meta.object_name.lower()
    elif isinstance(o, (list, dict, set, QuerySet)):
        return "%s (%s item%s)" % (str(type(o)), len(o), pluralize(len(o)))
    else:
        return str(type(o))

def _hash(o, seen=None):
    if seen is None:
        seen = set()
    if id(o) in seen:
        return "recursion on %s" % id(o)
    else:
        seen.add(id(o))
    print "h%s" % o
    try:
        return hash(o)
    except TypeError:
        pass
    if isinstance(o, dict):
        return ('dict', (tuple((_hash(k, seen), _hash(v, seen)) for k,v in sorted(o.items()))))
    elif isinstance(o, list):
        return ('list', tuple(_hash(v, seen) for v in o))
    elif isinstance(o, set):
        return ('set', tuple(_hash(v, seen) for v in sorted(o)))
    else:
        raise TypeError, "Unable to hash %s" % o


def _context_helper(path, o, depth, seen, result):
    if depth > MAX_DEPTH:
        result.append("<tr><td>Too much nesting in context</td><td>Giving up.</td><td>&nbsp;</td></tr>")
        return
    h = _hash(o)
    if h in seen:
        result.append("<tr><td>%s</td><td>Previously reached.</td><td>Skipped</td></tr>" % (force_escape(".".join(path)),))
        return
    seen.add(h)
    result.append("<tr><td>%s</td><td>%s</td><td>" % (force_escape(".".join(path)), force_escape(_type_helper(o)[:100])))
    if isinstance(o, (list, dict, set, tuple)):
        result.append("<table>")
        if isinstance(o, dict):
            iter_ = lambda o:o.items()[:100]
        elif isinstance(o, tuple):
            iter_ = lambda o:list(enumerate(o))
        else:
            iter_ = lambda o:list(enumerate(o))[:5]
        for k,v in iter_(o):
            _context_helper(path + [k], v, depth+1, seen, result)
        result.append("</table>")
    elif isinstance(o, (QuerySet, Model)):
        if isinstance(o, Model):
            meta = o._meta
        else:
            meta = o.model._meta
        app_label, model_name = meta.app_label, meta.object_name.lower()
        url = urlresolvers.reverse('django-admindocs-models-detail', args=[app_label, model_name])
        label = "%s.%s" % (app_label, model_name)
        result.append("<a href='%s'>doc for %s</a>" % (url, label))
    elif isinstance(o, Form):
        result.append("<table><tr><th>name</th><th>type</th><th>value</th></tr>")
        for bound_field in o:
            _context_helper(path + [bound_field.name], bound_field, depth+1, seen, result)
        result.append("</table>")
    else:
        if hasattr(o, '__unicode__'):
            val = unicode(o)
        else:
            val = repr(o)
        if len(val) > 100:
            val = val[:97] + "..."
        result.append(force_escape(val))
    result.append("</td></tr>")

def context_helper(context):
    result = [] #(o, repr, link)
    seen = set()
    if not context:
        result.append("<p>No context given.</p>")
    else:
        result.append("<p>Context includes:</p>")
        result.append("<table><tr><th>name</th><th>type</th><th>value</th></tr>")
        for k,v in context.items():
            _context_helper([k], context[k], 0, seen, result)
        result.append("</table><p>Context finished.</p>")
    return mark_safe("\n".join(result))