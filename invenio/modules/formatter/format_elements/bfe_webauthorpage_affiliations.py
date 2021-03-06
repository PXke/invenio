# -*- coding: utf-8 -*-
##
## This file is part of Invenio.
## Copyright (C) 2011 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of the
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
"""BibFormat element - Prints authors
"""

from cgi import escape
import pickle

def format_element(bfo):
    """
    Return list of profile affiliations.
    """
    fields = bfo.fields("100__")
    fields2 = bfo.fields("700__")
    dic = {}
    recid = bfo.recID

    for f in fields + fields2:
        if 'a' in f:
            if 'u' in f:
                u = f['u']
            else:
                u = ''
            try:
                dic[f['a']] += u
            except KeyError:
                dic[f['a']] = [u]

    return pickle.dumps([recid, dic])

#    for field in fields:
#        if field.has_key('a') and field.has_key('u'):
#            affil.append("100__ $$a" + field['a'] + " $$u" + field['u'] + "<br />")
#        else:
#            if field.has_key('a'):
#                affil.append("100__ $$a" + field['a'] + "<br />")
#            if field.has_key('u'):
#                affil.append("100__ $$u" + field['u'] + "<br />")
#    for field2 in fields2:
#        if field2.has_key('a') and field2.has_key('u'):
#            affil.append("700__ $$a" + field2['a'] + " $$u" + field2['u'] + "<br />")
#        else:
#            if field2.has_key('a'):
#                affil.append("700__ $$a" + field2['a'] + "<br />")
#            if field2.has_key('u'):
#                affil.append("700__ $$u" + field2['u'] + "<br />")
#
#    return separator.join(affil)

def escape_values(bfo):
    """
    Called by BibFormat in order to check if output of this element
    should be escaped.
    """
    return 0
