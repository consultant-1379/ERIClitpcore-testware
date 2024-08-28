##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

import os
import imp
from litp.core.plugin import Plugin
#from litp.core.validators import ValidationError

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class PluginMaker(type):
    """dynamically generates a new plugin class for each story/test"""

    def __new__(mcs, name, base, dct):
        """overwrites the __new__ magic method to create a new class"""

        log.trace.info("GENERATE: Plugin Class \"{0}\"".format(name))
        return super(PluginMaker, mcs).__new__(mcs, name, base, dct)


class TestModulePlugin(Plugin):
    """a generic test module plugin for executing plugin_api tests"""

    _instances = dict()  # a dictionary of class instances
    _stories = dict()  # a dictionary of query items per story index
    _lock_tasks = list()  # a list of query items that require lock tasks

    def _make_class(self, story_id):
        """calls the plugin maker meta class to generate a new plugin class"""

        # check if there is an instantiated class and, if not, generate and
        # instantiate a new one
        if not TestModulePlugin._instances or \
                not TestModulePlugin._instances[story_id]:
            # plugin class name is of the format 'StoryNumberPlugin'
            class_name = '{0}Plugin'.format(
                ''.join(story_id.split('-')).title()
            )
            # create the class and return its instance
            cls = PluginMaker(class_name, (Plugin, ), {})()
            TestModulePlugin._instances[story_id] = cls
        # if one already exists, just get that
        else:
            cls = TestModulePlugin._instances[story_id]

        return cls

    def _query(self, plugin_api_context):
        """queries the model for any test-module item in the tree"""

        # query for all items of item type test-module
        modelitems = plugin_api_context.query('test-module')
        if not modelitems:
            return []
        # get a set of unique story IDs that are in the model for test
        story_ids = [modelitem.tc_story for modelitem in modelitems]
        require_lock_tasks = [
            modelitem for modelitem in modelitems if modelitem.lock == 'true'
        ]
        story_ids = list(set(story_ids))
        # for each story under test get a list of model items per id
        for story_id in story_ids:
            if story_id not in TestModulePlugin._stories.keys():
                TestModulePlugin._stories[story_id] = list()
            for modelitem in modelitems:
                if modelitem.tc_story == story_id:
                    TestModulePlugin._stories[story_id].append(modelitem)
                # check if lock tasks are required from the plugin
                if require_lock_tasks:
                    if modelitem in require_lock_tasks:
                        TestModulePlugin._lock_tasks.extend(require_lock_tasks)

    def create_configuration(self, plugin_api_context):
        """
        generic plugin create_configuration; calls the required method and
        returns the tasks
        """

        tasks = list()
        self._query(plugin_api_context)
        # for each story create a new plugin (if one doesn't already exist)
        for story_id in TestModulePlugin._stories.keys():
            cls = self._make_class(story_id)
            # for each model item for the story add the methods to the plugin
            # class instance
            for modelitem in TestModulePlugin._stories[story_id]:
                method = add_method(cls, modelitem, 'cfg')
                # get all tasks to be put into the plan
                tasks.extend(
                    getattr(cls, method.__name__)(
                        modelitem,
                        plugin_api_context
                    )
                )

        return tasks

    def create_lock_tasks(self, plugin_api_context, node):
        """
        generic plugin create_lock_tasks; calls the required method and returns
        the lock/unlock tasks
        """

        tasks = list()
        self._query(plugin_api_context)
        if TestModulePlugin._lock_tasks:
            # for each story create a new plugin (if one doesn't already exist)
            for story_id in TestModulePlugin._stories.keys():
                cls = self._make_class(story_id)
                # for each model item for the story add the methods to the
                # plugin class instance
                for modelitem in TestModulePlugin._stories[story_id]:
                    if modelitem in TestModulePlugin._lock_tasks:
                        method = add_method(cls, modelitem, 'lck')
                        # get all tasks to be put into the plan
                        tasks.extend(
                            getattr(cls, method.__name__)(
                                modelitem,
                                plugin_api_context,
                                node
                            )
                        )
        if tasks:
            return tuple(tasks)

        return ()


def load_module(module_name):
    """lookup and load the module for the story under test"""

    # gets the test-module plugin python source file location and loads, using
    # the imp module, the specific methods required to test the story

    filepath = os.path.abspath(os.path.dirname(__file__))
    log.trace.info(
        "LOCATE: Python source module \"LITPCDS-{0}\"".format(module_name)
    )
    file_obj, filename, description = imp.find_module(module_name, [filepath])
    try:
        module = imp.load_module(module_name, file_obj, filename, description)
        log.trace.info(
            "SUCCESS: Loaded module \"{0}\" from \"{1}\"".format(
                file_obj,
                filename
            )
        )

        return module

    except ImportError, err:
        log.trace.error(
            "Import Error for module \"{0}\": {1}".format(module_name, err)
        )

        return None

    return None


def get_method(module_name, method_name):
    """retrieve the required plugin specific method to execute the tests"""

    # after succesfully loading the story module, it retrieves the required
    # method on a per test basis

    method = [
        getattr(module_name, method_n) for method_n in dir(module_name) \
        if method_n == method_name
    ][0]
    if not method:
        log.trace.error("NOT FOUND: Method \"{0}\"".format(method_name))
        return None
    log.trace.info(
        "FOUND: Method \"{0}\" for test execution".format(method)
    )

    return method


def add_method(cls, mdlitm, plugin_method):
    """
    find the modules/methods required for the story tests execution and add
    them to the generated plugin
    """

    # adds the required methods for each story to the dynamically generated
    # class and returns it for execution

    module_name = mdlitm.tc_story.split('-')[-1]  # story number
    kind = mdlitm.tc_type[0]  # test type (positve|negative)
    description = mdlitm.tc_description  # test description/name
    # the above attributes are used to locate the method required for the test,
    # along with plugin method type 'cfg' == 'create_configuration' OR
    # 'lck' == 'create_lock_tasks'
    method_name = '{0}_{1}_{2}_{3}'.format(
        plugin_method,
        mdlitm.tc_name,
        kind,
        description
    )
    module = load_module(module_name)
    if not module:
        return None
    method = get_method(module, method_name)
    if not method:
        return None
    # check if we need a 'create_configuration' or 'create_lock_tasks' method
    if plugin_method == 'cfg':
        method.__name__ = 'create_configuration'
    elif plugin_method == 'lck':
        method.__name__ = 'create_lock_tasks'
    log.trace.info(
        "ADD METHOD: \"{0}\" attribute to instance \"{1}\"".format(
            method.__name__,
            cls
        )
    )
    # method found and added to dynamic class instance as either
    # 'create_configuration' OR 'create_lock_tasks'
    setattr(cls, method.__name__, method)
    log.trace.info(
        "PLUGIN: Plugin Class instance \"{0}\" with \"{1}\"".format(
            cls.__class__.__name__,
            dir(cls)
        )
    )
    log.trace.info(
        "EXECUTE TEST: \"LITPCDS-{0}.{1}\"".format(module_name, method_name)
    )

    return method
