# -*- coding: utf-8 -*-
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

""" Implements a workflow for testing """

from invenio.modules.workflows.tasks.workflows_tasks import (start_workflow,
                                                             wait_for_a_workflow_to_complete,
                                                             get_list_of_workflows_to_wait,
                                                             write_something_generic,
                                                             log_info,
                                                             workflows_reviews,
                                                             get_nb_workflow_created,
                                                             num_workflow_running_greater,
                                                             get_nb_workflow_running,
                                                             wait_for_workflows_to_complete)

from invenio.modules.workflows.tasks.logic_tasks import simple_for, end_for, workflow_if, workflow_else


class test_workflow_workflows_errors(object):
    """
    Test workflow for unit-tests.
    """
    workflow = [
        simple_for(0, 5, 1, "X"),
        [
            start_workflow("test_workflow_error", 22),
            log_info(get_nb_workflow_created),
        ],
        end_for,

        simple_for(0, 5, 1),
        [
            write_something_generic(["We are waiting for ", get_list_of_workflows_to_wait], [log_info]),
            wait_for_a_workflow_to_complete(0.1),
        ],
        end_for,

        workflows_reviews(False, False)
    ]
