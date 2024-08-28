##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################
from litp.core.plugin import Plugin
from litp.core.task import ConfigTask
from litp.core.task import CallbackTask
from litp.plan_types.deployment_plan import deployment_plan_tags


class Story7394Plugin(Plugin):

    def _cb1(self, *args, **kwargs):
        pass

    def create_configuration(self, api):
        tasks = []
        ms = api.query("ms")[0]
        for dummy_package in ms.query("story7394"):
            if dummy_package.is_applied():
                continue
            task1 = ConfigTask(
                ms, dummy_package,
                "ConfigTask call_type_1",
                "notify", "foo",
                name=dummy_package.name
            )
            task2 = CallbackTask(
                dummy_package, "Callback _cb1",
                self._cb1
            )
            task3 = ConfigTask(
                ms, dummy_package,
                "ConfigTask call_type_2",
                "notify", "bar",
                name=dummy_package.name + '_2'
            )
            task4 = ConfigTask(
                ms, dummy_package,
                "ConfigTask call_type_3",
                "notify", "zar",
                name=dummy_package.name + '_3',
                tag_name=deployment_plan_tags.MS_TAG
            )
            task5 = ConfigTask(
                ms, dummy_package,
                "ConfigTask call_type_4, persist flag set to False",
                "notify", "baz",
                name=dummy_package.name + '_4'
            )
            task5.persist = False
            tasks.append(task5)
            task1.requires.add(task4)
            task2.requires.add(task1)
            task3.requires.add(task2)
            tasks.extend([task1, task2, task3, task4])
        return tasks
