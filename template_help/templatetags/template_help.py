import datetime
from decimal import Decimal
from django.http import HttpRequest
from django import template
from django.template.defaultfilters import mark_safe, force_escape, pluralize
from django.db.models.query import QuerySet
from django.forms import BaseForm, Field
from django.db.models import Model
from django.core import urlresolvers
from django.core.paginator import Paginator, Page

register = template.Library()

def is_iterable(x):
    "A implementation independent way of checking for iterables"
    try:
        iter(x)
        return True
    except (SystemExit, KeyboardInterrupt):
        raise
    except:
        pass
    return False

@register.tag
def context_help(parser, token):
    """
    Renders a table listing each item in the context, along with a synopsis of the value.
    e.g. Context({'users':User.objects.all()}) -> 
    <table>
    <tr><td>users</td><td>Queryset of XXX <a href="/admin/doc/models/auth.user/">auth.user</a></td></tr>
    </table>
    
    The idea is that a Django dev can write views up to a context, and provide a stub template to a designer; 
    the designer could then use the help provided by this tag to work with the given context.

    Normally, lists rendered as just counts w/ the 0th item taken as an examplar.
    Tuples are listed out, unless they are particularly long, in which case an exemplar is shown.
    Dictionaries are always listed out.  Doubly-nested dicts are not shown.
      (If you're nesting context that much, you're probably doing something silly.)
    Too bad forms aren't registered in Admin docs, but at least the fields are listed out here.
    """
    return ContextHelpNode()
    
class ContextHelpNode(template.Node):
    def render_explanation(self, o):
        if isinstance(o, HttpRequest):
            return "<a href='http://docs.djangoproject.com/en/dev/ref/request-response/#ref-request-response'>request object</a>"
        elif isinstance(o, (QuerySet,Model)):
            if isinstance(o, QuerySet):
                prefix = "Queryset of "
                o = o.model
            else:
                m = o
            #link to model docs
            app_label, model_name = o._meta.app_label, o._meta.object_name.lower()
            url = urlresolvers.reverse('django-admindocs-models-detail', args=[app_label, model_name])
            return "<a href='%s'>%s</a>" % (force_escape(url), 
                                            force_escape("%s.%s" % (app_label, model_name)))
        elif isinstance(o, BaseForm):
            return "<p>%s fields:</p>\n<ul>%s</ul>" % (
            o.__class__.__name__,
            "\n".join(["<li>%s</li>" % force_escape(field) for field in o.fields])
            )
        elif isinstance(o, (set, list, tuple, dict)):
            return "group of %s items" % len(o)
        elif isinstance(o, str):
            return force_escape(unicode(o, 'utf-8'))
        elif isinstance(o, (unicode, int, Decimal, float, datetime.date, datetime.time, datetime.datetime)):
            return force_escape(unicode(o))
        else:
            type_ = type(o)

            str_ = unicode(o)
            return force_escape("%s: %s" % (type_, str_))

    def render_row(self, results, label, explanation):
        results.append("<tr><td class='label'>%s</td><td class='explanation'>%s</td></tr>" % (force_escape(label),explanation))

    def render_item(self, results, label, o):
        if isinstance(o, BaseForm):
            self.render_row(results, label, self.render_explanation(o))
        elif isinstance(o, tuple):
            if len(o) < 10:
                if len(o) == 0:
                    self.render_row(results, label, "Empty tuple")
                    return ""
                self.render_row(results, label, force_escape("tuple %s:%s") + ",".join([(i,self.render_explanation(val)) 
                                                for (i,val) in enumerate(o)]))
            else:
                self.render_row(results, label, "Long tuple-- %s items -- e.g. %s.0=>%s " % (len(o), force_escape(label), self.render_explanation(o[0])))
        elif isinstance(o, (set, list, QuerySet)) or (is_iterable(o) and not isinstance(o, basestring)):
            if isinstance(o, set):
                seq_type = "Set"
            elif isinstance(o, list):
                seq_type = "List"
            elif isinstance(o, QuerySet):
                seq_type = "Queryset"
            else:
                seq_type = "Sequence (%s)" % (o,)
            try:
                o_l = len(o)
            except TypeError:
                o_l = "<Unknown>"
            if o_l == 0:
                self.render_row(results, label, force_escape("Empty %s" % seq_type))
                return
            o = iter(o).next()
            self.render_row(results, label, force_escape("%s of %s " % (seq_type, o_l)) + (
                            self.render_explanation(o)))
        else:
            self.render_row(results, label, self.render_explanation(o))
    

    def render(self, context):
        #flatten context into a standard dict.
        if isinstance(context, dict):
            d = context
        else:
            d = {}
            for inner_d in reversed(context.dicts):
                d.update(inner_d)                
        results = ["<table class='context_help'>"]
        if not d:
            return "<p>Empty context</p>"
        for k,v in sorted(d.items(), key=lambda t: t[0].lower()):
            if isinstance(v,dict):
                results.append("<tr><td class='label'>%s</td><td class='explanation verbose'><table>" % force_escape(k))
                    
                for inner_k, inner_v in v.items():
                    label = "%s.%s" % (k, inner_k)
                    if isinstance(inner_v, dict):
                        self.render_row(results, "Too many nested dicts", "stopping at %s" % (label,))
                    else:
                        self.render_item(results, label, inner_v)
                results.append("</table></td></tr>")
            else:
                self.render_item(results, k, v)
        results.append("</table>")
        return "\n".join(results)
