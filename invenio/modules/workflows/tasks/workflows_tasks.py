# -*- coding: utf-8 -*-
## This file is part of Invenio.
## Copyright (C) 2013, 2014 CERN.
##
## Invenio is free software; you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation; either version 2 of t
## License, or (at your option) any later version.
##
## Invenio is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with Invenio; if not, write to the Free Software Foundation, Inc.,
## 59 Temple Place, Suite 330, Boston, MA 02111 1307, USA.

import six

from invenio.modules.workflows.models import (BibWorkflowObject,
                                              BibWorkflowEngineLog,
                                              ObjectVersion)
from invenio.modules.workflows.api import start_delayed
from invenio.modules.workflows.errors import WorkflowError

from time import sleep


def interrupt_workflow(obj, eng):
    """
    Small function mailny for testing which stops the workflow.
    The object will be in the state HALTED.

    :param obj: BibworkflowObject to process
    :param eng: BibWorkflowEngine processing the object
    """
    eng.halt("interrupting workflow.")


def get_nb_workflow_created(obj, eng):
    """
    This function will return the number of workflows created
    for this instance.

    :param obj: BibworkflowObject to process
    :param eng: BibWorkflowEngine processing the object
    :return the number of workflow created since the last clean.
    """
    try:
        return eng.extra_data["_nb_workflow"]
    except KeyError:
        return "0"


def num_workflow_running_greater(num):
    """
    This function has been created to correct the problem of saturation
    of messaging queue which  can lead to the complete destruction of
    the computing node.

    This function should be used with the function to create workflow and wait
    for workflow to finish.

    This allows to control the number of workflow in the messaging queue

    This function will just return True if the number of workflow
    in the messaging queue is higher than num or False.

    :param num: the number that you want to compare with the number of workflows in
    the message queue
    :type num: number
    :return True if you need to wait ( number of workflow in message queue greater
    than num) or false if you don't need to wait.
    """

    def _num_workflow_running_greater(obj, eng):
        try:
            if (eng.extra_data["_nb_workflow"] - eng.extra_data["_nb_workflow_finish"]) > num:
                return True
            else:
                return False
        except KeyError:
            return False

    return _num_workflow_running_greater


def get_nb_workflow_running(obj, eng):
    """
    :param obj: BibworkflowObject being process
    :param eng: BibWorkflowEngine processing the object
    """
    try:
        return eng.extra_data["_nb_workflow"] - eng.extra_data["_nb_workflow_finish"]
    except KeyError:
        return "0"


def start_workflow(workflow_to_run="default", data=None, copy=True, **kwargs):
    """
     This function allow you to run a new asynchronous workflow, this
     will be run on the celery node configurer into invenio
     configuration.

     :param workflow_to_run: The first argument is the name of the workflow to run.

     :param data: The second one is the data to use for this workflow.

     :param copy: The copy parameter allow you to pass to the workflow  a copy
     of the obj at the moment of the call .

     :param kwargs: **kargs allow you to add some key:value into the extra data of
     the object.
     """

    def _start_workflow(obj, eng):

        if copy:
            myobject = BibWorkflowObject.create_object_revision(obj,
                                                                version=ObjectVersion.INITIAL,
                                                                data_type="record")
        else:
            myobject = BibWorkflowObject()

        if data:
            myobject.set_data(data)
            myobject.save()

        workflow_id = start_delayed(workflow_to_run,
                                    data=[myobject],
                                    stop_on_error=True,
                                    module_name=eng.module_name,
                                    **kwargs)

        eng.log.info("Workflow launched")
        try:
            eng.extra_data["_workflow_ids"].append(workflow_id)
        except KeyError:
            eng.extra_data["_workflow_ids"] = [workflow_id]

        try:
            eng.extra_data["_nb_workflow"] += 1
        except KeyError:
            eng.extra_data["_nb_workflow"] = 1

        if "_nb_workflow_failed" not in eng.extra_data:
            eng.extra_data["_nb_workflow_failed"] = 0
        if "_nb_workflow_finish" not in eng.extra_data:
            eng.extra_data["_nb_workflow_finish"] = 0
        if "_uuid_workflow_crashed" not in eng.extra_data:
            eng.extra_data["_uuid_workflow_crashed"] = []
        if "_uuid_workflow_succeed" not in eng.extra_data:
            eng.extra_data["_uuid_workflow_succeed"] = []

    return _start_workflow


def wait_for_workflows_to_complete(obj, eng):
    """
    This function wait all the asynchronous workflow launched.
    It acts like a barrier

    :param obj: BibworkflowObject being process
    :param eng: BibWorkflowEngine processing the object
    """
    if '_workflow_ids' in eng.extra_data:
        for workflow_id in eng.extra_data['_workflow_ids']:
            workflow_result_management(workflow_id, eng)
    else:
        eng.extra_data["_nb_workflow"] = 0
        eng.extra_data["_nb_workflow_failed"] = 0
        eng.extra_data["_nb_workflow_finish"] = 0


def wait_for_a_workflow_to_complete_obj(obj, eng):
    """
    This function wait for the asynchronous workflow specified
    in obj.data (asyncresult)
    It acts like a barrier

    :param obj: BibworkflowObject to process
    :param eng: BibWorkflowEngine processing the object
    """
    if not obj.data:
        eng.extra_data["_nb_workflow"] = 0
        eng.extra_data["_nb_workflow_failed"] = 0
        eng.extra_data["_nb_workflow_finish"] = 0
        return None
    workflow_result_management(obj.data, eng)


def wait_for_a_workflow_to_complete(scanning_time=0.5):
    """

    :param scanning_time: time value in second to define which interval
    is used, to look into the message queue for finished workflows.
    :type scanning_time: number
    :return:
    """

    def _wait_for_a_workflow_to_complete(obj, eng):
        """
        This function wait for the asynchronous workflow specified
        in obj.data (asyncresult)
        It acts like a barrier
        :param obj: BibworkflowObject to process
        :param eng: BibWorkflowEngine processing the object
        """
        if '_workflow_ids' in eng.extra_data:
            to_wait = None
            i = 0
            while not to_wait and len(eng.extra_data["_workflow_ids"]) > 0:
                for i in range(0, len(eng.extra_data["_workflow_ids"])):
                    if eng.extra_data["_workflow_ids"][i].status == "SUCCESS":
                        to_wait = eng.extra_data["_workflow_ids"][i]
                        break
                    if eng.extra_data["_workflow_ids"][i].status == "FAILURE":
                        to_wait = eng.extra_data["_workflow_ids"][i]
                        break
                sleep(scanning_time)
            if not to_wait:
                return None
            workflow_result_management(to_wait, eng)

            del eng.extra_data["_workflow_ids"][i]

        else:
            eng.extra_data["_nb_workflow"] = 0
            eng.extra_data["_nb_workflow_failed"] = 0
            eng.extra_data["_nb_workflow_finish"] = 0

    return _wait_for_a_workflow_to_complete


def workflow_result_management(async_result, eng):
    """
    This function is here mainly to factorize the code .

    :param async_result: asynchronous result that we want to query to
    get data.
    :param eng: workflowenginne for loging and state change.
    """
    try:
        engine = async_result.get()
        eng.extra_data["_nb_workflow_finish"] += 1
        eng.extra_data["_uuid_workflow_succeed"].append(engine.uuid)
    except WorkflowError as e:
        eng.log.error("Error: Workflow failed %s" % str(e))
        workflowlog = BibWorkflowEngineLog.query.filter(
            BibWorkflowEngineLog.id_object == e.id_workflow
        ).filter(BibWorkflowEngineLog.log_type >= 40).all()

        for log in workflowlog:
            eng.log.error(log.message)

        for i in e.payload:
            eng.log.error(str(i))
        eng.extra_data["_uuid_workflow_crashed"].append(e.id_workflow)
        eng.extra_data["_nb_workflow_failed"] += 1
        eng.extra_data["_nb_workflow_finish"] += 1
    except Exception as e:
        eng.log.error("Error: Workflow failed %s" % str(e))
        eng.extra_data["_nb_workflow_failed"] += 1
        eng.extra_data["_nb_workflow_finish"] += 1


def write_something_generic(messagea, func):
    """
    This function allows you to write a message where you want.
    This function support the multicasting.

    Messagea is a string or a list of string  and function that will be concatenate
    in one and only string.

    Func is the list of the functions that will be used to send the message. The function
    should always take in parameter a string which is the message.

    :param func: the list of function that will be used to propagate the message
    :type func: list of functions or a functions.
    :param messagea: the message that you want to propagate
    :type messagea: list of strings and functions.
    """

    def _write_something_generic(obj, eng):
        if isinstance(messagea, six.string_types):
            if isinstance(func, list):
                for function in func:
                    function(messagea)
            else:
                func(messagea)
            return None

        if not isinstance(messagea, list):
            if callable(messagea):
                func_messagea = messagea
                while callable(func_messagea):
                    func_messagea = func_messagea(obj, eng)
                if isinstance(func, list):
                    for function in func:
                        function(func_messagea)
                else:
                    func(func_messagea)
            return None

        if len(messagea) > 0:
            temp = ""
            for func_messagea in messagea:
                if callable(func_messagea):
                    while callable(func_messagea):
                        func_messagea = func_messagea(obj, eng)
                    temp += str(func_messagea)
                elif isinstance(func_messagea, six.string_types):
                    temp += func_messagea
            if isinstance(func, list):
                for function in func:
                    function(temp)
            else:
                func(temp)
            return None

    return _write_something_generic


def get_list_of_workflows_to_wait(obj, eng):
    """
     Return a list of asyncresult corresponding to running
     asynchrnous workflow

    :param obj: Bibworkflow Object to process
    :param eng: BibWorkflowEngine processing the object
     """
    return eng.extra_data["_workflow_ids"]


def get_status_async_result_obj_data(obj, eng):
    """
    :param obj: Bibworkflow Object to process
    :param eng: BibWorkflowEngine processing the object
    """
    return obj.data.state


def get_workflows_progress(obj, eng):
    """
    :param obj: Bibworkflow Object to process
    :param eng: BibWorkflowEngine processing the object
    """
    try:
        return (eng.extra_data["_nb_workflow_finish"] * 100.0) / (eng.extra_data["_nb_workflow"])
    except KeyError:
        return "No progress (key missing)"
    except ZeroDivisionError:
        return "No workflows"


def workflows_reviews(stop_if_error=False, clean=True):
    """
    This function just give you a little review of you children workflows.
    This function can be used to stop the workflow if a child has crashed.

    :param clean: optional, allows the cleaning of data about workflow for example
     start again from clean basis.
    :type clean: bool
    :param stop_if_error: give to the function the indication it it should stop
    if a child workflow has crashed.
    :type stop_if_error: bool
    """

    def _workflows_reviews(obj, eng):
        """
         This function write a  little report about
         asynchronous workflows in this main workflow
         Raise an exception if a workflow is gone rogue
         """
        if eng.extra_data["_nb_workflow"] == 0:
            raise WorkflowError("Nothing has been harvested ! Look into logs for errors !", eng.uuid, obj.id)
        eng.log.info("%s / %s failed" % (eng.extra_data["_nb_workflow_failed"], eng.extra_data["_nb_workflow"]))

        if eng.extra_data["_nb_workflow_failed"] and stop_if_error:
            raise WorkflowError(
                "%s / %s failed" % (eng.extra_data["_nb_workflow_failed"], eng.extra_data["_nb_workflow"]),
                eng.uuid, obj.id, payload=eng.extra_data["_uuid_workflow_crashed"])
        obj.add_task_result("review_workflow",
                            {"failed": eng.extra_data["_nb_workflow_failed"], "total": eng.extra_data["_nb_workflow"]})
        if clean:
            eng.extra_data["_nb_workflow_failed"] = 0
            eng.extra_data["_nb_workflow"] = 0
            eng.extra_data["_nb_workflow_finish"] = 0

    return _workflows_reviews


def log_info(message):
    """
    A simple function to log a simple thing,
    if you want more sophisticated way, thanks to see
    the function write_something_generic.

    :param message: this value represent what we want to log,
    if meessage is a function then it will be executed.
    :type message: str or function
    :return:
    """

    def _log_info(obj, eng):
        messagea = message
        while callable(messagea):
            messagea = messagea(obj, eng)
        eng.log.info(messagea)

    return _log_info
