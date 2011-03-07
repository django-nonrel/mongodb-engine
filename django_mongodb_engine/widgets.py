from django.conf import settings
from django.forms import widgets
from django.db import models

from django.utils.safestring import mark_safe

import warnings
warnings.warn("django_mongodb_engine.widgets is deprecated and will be removed "
              "in version 0.5", DeprecationWarning)

class DictWidget(widgets.Widget):
    def value_from_datadict(self, data, files, name):
        if data.has_key("%s_rows" % name):
            returnlist ={}
            rows= int( data["%s_rows" % name])
            while rows > 0:
                rows -= 1
                rowname = "%s_%d" % (name, rows )
                if data.has_key("%s_key" % rowname ) :
                    k = data["%s_key" % rowname]
                    if k != "":
                        v = None
                        if data.has_key("%s_value" % rowname ) :
                            v = data["%s_value"%rowname]
                        returnlist[k]=v
            rowname = "%s_new" % name
            if data.has_key("%s_key" % rowname ) :
                k = data["%s_key" % rowname]
                if k != "":
                    v = None
                    if data.has_key("%s_value" % rowname ) :
                        v = data["%s_value"%rowname]
                    returnlist[k]=v

            return returnlist
        else:
            return None

    def render(self, name, value, attrs=None):

        htmlval="<table><tr><td>#</td><td>Key</td><td>Value</td></tr>"

        linenum=0
        idname = attrs['id']
        if (value is not None) and (type(value).__name__=='dict') :
            for key, val in value.items():
                idname_row = "%s_%d" % ( idname, linenum )

                htmlval += '<tr><td><label for="%s_key">%d</label></td><td><input type="txt" id="%s_key" name="%s_%d_key" value="%s" /></td>' % (
                        idname_row, linenum ,idname_row, name,linenum, key )
                htmlval += '<td><input type="txt" id="%s_value" name="%s_%d_value" value="%s" /></td></tr>' % (
                        idname_row, name,linenum, val)
                linenum += 1
        idname_row = "%s_new" % ( idname )

        htmlval += '<tr><td><label for="%s_key">new</label></td><td><input type="txt" id="%s_key" name="%s_new_key" value="" /></td>' % (
                idname_row, idname_row, name)
        htmlval += '<td><input type="txt" id="%s_value" name="%s_new_value" value="" /></td></tr>' % (
                idname_row, name )

        htmlval += "</table>"
        htmlval += "<input type='hidden' name='%s_rows' value='%d'>" % ( name, linenum )
        return mark_safe(htmlval)
