# -*- coding: utf-8 -*-
##
## This file is part of Invenio.
## Copyright (C) 2013, 2014 CERN.
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

from __future__ import absolute_import

from cerberus import Validator
from flask import request, current_app
from flask.ext.login import current_user
from flask.ext.restful import Resource, abort, marshal_with, fields, reqparse
from flask.ext.restful.utils import unpack
from functools import wraps
from werkzeug.utils import secure_filename

from invenio.ext.restful import require_api_auth, error_codes, require_oauth_scopes, require_header

from . import errors
from .api import Document


class APIValidator(Validator):
    """
    Adds new datatype 'raw', that accepts anything.
    """
    def _validate_type_any(self, field, value):
        pass


#
# Decorators
#
def error_handler(f):
    """
    Decorator to handle deposition exceptions
    """
    @wraps(f)
    def inner(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except errors.DocumentNotFound as e:
            abort(404, message="Document does not exists.", status=404)
        except Exception as e:
            current_app.logger.error(e)
            if len(e.args) >= 1:
                abort(400, message=e.args[0], status=400)
            else:
                abort(500, message="Internal server error", status=500)
    return inner


def filter_errors(result):
    """
    Extract error messages from a draft.process() result dictionary.
    """
    error_messages = []
    for field, msgs in result.get('messages', {}).items():
        if msgs.get('state', None) == 'error':
            for m in msgs['messages']:
                error_messages.append(dict(
                    field=field,
                    message=m,
                    code=error_codes['validation_error'],
                ))
    return error_messages


# =========
# Mix-ins
# =========
document_decorators = [
    require_api_auth(),
    error_handler,
]


# =========
# Resources
# =========
class DocumentListResource(Resource):
    """
    Collection of documents
    """
    method_decorators = document_decorators

    def get(self):
        """
        List all files.
        """
        result = Document.storage_engine.model.query.all()
        return filter(
            lambda x: x.get('creator') == current_user.get_id(),
            map(lambda o: Document.get_document(o.id).dumps(), result)
        )

    @require_header('Content-Type', 'application/json')
    def post(self):
        """
        Create a new document
        """
        abort(405)

    @require_header('Content-Length', lambda v: v is not None)
    def put(self):
        d = Document.create({'deleted': False})
        d.setcontents(request.stream, name=request.args.get('name'))
        return d.dumps()

    def delete(self):
        abort(405)

    def head(self):
        abort(405)

    def options(self):
        abort(405)

    def patch(self):
        abort(405)


class DocumentFileResource(Resource):
    """
    Represent a document file
    """
    method_decorators = document_decorators

    def get(self, document_uuid):
        """ Stream a document file. """
        d = Document.get_document(document_uuid)
        return d.dumps()

    def delete(self, document_uuid):
        """ Delete existing deposition file. """
        d = Document.get_document(document_uuid)
        d.delete()
        return d.dumps()

    def put(self, document_uuid):
        """ Overwrite document file content. """
        d = Document.get_document(document_uuid)
        d.setcontents(request.stream, name=request.args.get('name'))
        return d.dumps()

    def post(self):
        abort(405)

    def head(self, document_uuid):
        """ Return document metadata. """
        abort(405)

    def options(self, document_uuid):
        abort(405)

    def patch(self, document_uuid):
        """ Create new document version. """
        abort(405)


#
# Register API resources
#
def setup_app(app, api):
    api.add_resource(
        DocumentListResource,
        '/api/document/',
    )
    api.add_resource(
        DocumentFileResource,
        '/api/document/<string:document_uuid>',
    )
