## -*- coding: utf-8 -*-
## This file is part of Invenio.
## Copyright (C) 2012, 2013 CERN.
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

import redis
import traceback

from six import iteritems

from .errors import WorkflowDefinitionError


# def generate_workflow_report(engine):
#
#     report = ""
#
#     if not isinstance(engine, BibWorkflowEngine) or isinstance(engine, Workflow):
#             engine = uui_to_workflow(engine)
#
#     write_message("ERROR HAPPEN")
#     write_message("____________Workflow log output____________")
#     workflow_id_preservation = e.id_workflow
#     workflowlog = BibWorkflowEngineLog.query.filter(BibWorkflowEngineLog.id_object == e.id_workflow) \
#         .filter(BibWorkflowEngineLog.log_type >= 40).all()
#
#     for log in workflowlog:
#         write_message(log.message)
#
#     for i in e.payload:
#         write_message("\n\n____________Workflow " + i + " log output____________")
#         workflowlog = BibWorkflowEngineLog.query.filter(BibWorkflowEngineLog.id_object == i) \
#             .filter(BibWorkflowEngineLog.log_type >= 40).all()
#         for log in workflowlog:
#             write_message(log.message)
#
#     write_message("ERROR HAPPEN")
#     write_message("____________Object log output____________")
#     objectlog = BibWorkflowObjectLog.query.filter(BibWorkflowObjectLog.id_object == e.id_object) \
#         .filter(BibWorkflowEngineLog.log_type >= 40).all()
#     for log in objectlog:
#         write_message(log.message)
#     execution_time = round(time.time() - start_time, 2)
#     write_message("Execution time :" + str(execution_time))
#
#

def session_manager(orig_func):
    """Decorator to wrap function with the session."""
    from invenio.ext.sqlalchemy import db

    def new_func(self, *a, **k):
        """Wrappend function to manage DB session."""
        try:
            resp = orig_func(self, *a, **k)
            db.session.commit()
            return resp
        except:
            db.session.rollback()
            raise

    return new_func


def tearDown(self):
        """ Clean up created objects """
        from invenio.modules.workflows.models import (BibWorkflowObject,
                                                      Workflow,
                                                      BibWorkflowEngineLog,
                                                      BibWorkflowObjectLog)
        from invenio.ext.sqlalchemy import db

        workflows = Workflow.get(Workflow.module_name == "unit_tests").all()
        for workflow in workflows:
            BibWorkflowObject.query.filter(
                BibWorkflowObject.id_workflow == workflow.uuid
            ).delete()

            objects = BibWorkflowObjectLog.query.filter(
                BibWorkflowObject.id_workflow == workflow.uuid
            ).all()
            for obj in objects:
                db.session.delete(obj)
            db.session.delete(workflow)

            objects = BibWorkflowObjectLog.query.filter(
                BibWorkflowObject.id_workflow == workflow.uuid
            ).all()
            for obj in objects:
                BibWorkflowObjectLog.delete(id=obj.id)
            BibWorkflowEngineLog.delete(uuid=workflow.uuid)
            # Deleting dumy object created in tests
        db.session.query(BibWorkflowObject).filter(
            BibWorkflowObject.id_workflow.in_([11, 123, 253])
        ).delete(synchronize_session='fetch')
        Workflow.query.filter(Workflow.module_name == "unit_tests").delete()
        db.session.commit()

class BibWorkflowObjectIdContainer(object):
    """
    This class is only made to be able to store a workflow ID and
    to retrieve easily the workflow from this ID. It is used maily
    to overide some problem with SQLAlchemy when we change of
    execution thread ( for example Celery )
    """

    def __init__(self, bibworkflowobject=None):
        if bibworkflowobject is not None:
            self.id = bibworkflowobject.id
        else:
            self.id = None

    def get_object(self):
        from invenio.modules.workflows.models import BibWorkflowObject

        if self.id is not None:
            return BibWorkflowObject.query.filter(BibWorkflowObject.id == self.id).one()
        else:
            return None

    def from_dict(self, dict_to_process):
        self.id = dict_to_process[str(self.__class__)]["id"]
        return self

    def to_dict(self):
        return {str(self.__class__): self.__dict__}


class WorkflowsTaskResult(object):
    """
    Class to contain the current task results.
    """

    def __init__(self, task_name, name, result):
        self.task_name = task_name
        self.name = name
        self.result = result


def get_workflow_definition(name):
    """ Tries to load the given workflow from the system. """
    from .loader import workflows

    try:
        return workflows[name]
    except Exception as e:
        raise WorkflowDefinitionError("Error with workflow '%s': %s\n%s" %
                                      (name, str(e), traceback.format_exc()),
                                      workflow_name=name)


## TODO special thanks to http://code.activestate.com/recipes/440514-dictproperty-properties-for-dictionary-attributes/
class dictproperty(object):
    class _proxy(object):
        def __init__(self, obj, fget, fset, fdel):
            self._obj = obj
            self._fget = fget
            self._fset = fset
            self._fdel = fdel

        def __getitem__(self, key):
            return self._fget(self._obj, key)

        def __setitem__(self, key, value):
            self._fset(self._obj, key, value)

        def __delitem__(self, key):
            self._fdel(self._obj, key)

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self._fget = fget
        self._fset = fset
        self._fdel = fdel
        self.__doc__ = doc

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self._proxy(obj, self._fget, self._fset, self._fdel)


def redis_create_search_entry(bwobject):
    redis_server = set_up_redis()

    extra_data = bwobject.get_extra_data()
    #creates database entries to not loose key value pairs in redis

    for key, value in iteritems(extra_data["redis_search"]):
        redis_server.sadd("holdingpen_sort", str(key))
        redis_server.sadd("holdingpen_sort:%s" % (str(key),), str(value))
        redis_server.sadd("holdingpen_sort:%s:%s" % (str(key), str(value),),
                          bwobject.id)

    redis_server.sadd("holdingpen_sort", "owner")
    redis_server.sadd("holdingpen_sort:owner", extra_data['owner'])
    redis_server.sadd("holdingpen_sort:owner:%s" % (extra_data['owner'],),
                      bwobject.id)
    redis_server.sadd("holdingpen_sort:last_task_name:%s" %
                      (extra_data['_last_task_name'],), bwobject.id)


def filter_holdingpen_results(key, *args):
    """Function filters holdingpen entries by given key: value pair.
    It returns list of IDs."""
    redis_server = set_up_redis()
    new_args = []
    for a in args:
        new_args.append("holdingpen_sort:" + a)
    return redis_server.sinter("holdingpen_sort:" + key, *new_args)


def get_redis_keys(key=None):
    redis_server = set_up_redis()
    if key:
        return list(redis_server.smembers("holdingpen_sort:%s" % (str(key),)))
    else:
        return list(redis_server.smembers("holdingpen_sort"))


def get_redis_values(key):
    redis_server = set_up_redis()
    return redis_server.smembers("holdingpen_sort:%s" % (str(key),))


def set_up_redis():
    """
    Sets up the redis server for the saving of the HPContainers

    @return: Redis server object.
    """
    from flask import current_app

    redis_server = redis.Redis.from_url(
        current_app.config.get('CACHE_REDIS_URL', 'redis://localhost:6379')
    )
    return redis_server


def empty_redis():
    redis_server = set_up_redis()
    redis_server.flushall()


def sort_bwolist(bwolist, iSortCol_0, sSortDir_0):
    if iSortCol_0 == 0:
        if sSortDir_0 == 'desc':
            bwolist.sort(key=lambda x: x.id, reverse=True)
        else:
            bwolist.sort(key=lambda x: x.id, reverse=False)
    elif iSortCol_0 == 1:
        pass
        # if sSortDir_0 == 'desc':
        #     bwolist.sort(key=lambda x: x.id_user, reverse=True)
        # else:
        #     bwolist.sort(key=lambda x: x.id_user, reverse=False)
    elif iSortCol_0 == 2:
        pass
        # if sSortDir_0 == 'desc':
        #     bwolist.sort(key=lambda x: x.id_user, reverse=True)
        # else:
        #     bwolist.sort(key=lambda x: x.id_user, reverse=False)
    elif iSortCol_0 == 3:
        pass
        # if sSortDir_0 == 'desc':
        #     bwolist.sort(key=lambda x: x.id_user, reverse=True)
        # else:
        #     bwolist.sort(key=lambda x: x.id_user, reverse=False)
    elif iSortCol_0 == 4:
        if sSortDir_0 == 'desc':
            bwolist.sort(key=lambda x: x.id_workflow, reverse=True)
        else:
            bwolist.sort(key=lambda x: x.id_workflow, reverse=False)
    elif iSortCol_0 == 5:
        if sSortDir_0 == 'desc':
            bwolist.sort(key=lambda x: x.id_user, reverse=True)
        else:
            bwolist.sort(key=lambda x: x.id_user, reverse=False)
    elif iSortCol_0 == 6:
        if sSortDir_0 == 'desc':
            bwolist.sort(key=lambda x: x.created, reverse=True)
        else:
            bwolist.sort(key=lambda x: x.created, reverse=False)
    elif iSortCol_0 == 7:
        if sSortDir_0 == 'desc':
            bwolist.sort(key=lambda x: x.version, reverse=True)
        else:
            bwolist.sort(key=lambda x: x.version, reverse=False)
    elif iSortCol_0 == 8:
        if sSortDir_0 == 'desc':
            bwolist.sort(key=lambda x: x.version, reverse=True)
        else:
            bwolist.sort(key=lambda x: x.version, reverse=False)
    elif iSortCol_0 == 9:
        if sSortDir_0 == 'desc':
            bwolist.sort(key=lambda x: x.version, reverse=True)
        else:
            bwolist.sort(key=lambda x: x.version, reverse=False)

    return bwolist


def parse_bwids(bwolist):
    import ast

    return list(ast.literal_eval(bwolist))



def generate_report_workflow():
    o=0
