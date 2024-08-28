##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from litp.core.extension import ModelExtension
from litp.core.model_type import ItemType
from litp.core.model_type import PropertyType
from litp.core.model_type import Property
from litp.core.model_type import View

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class TestModuleExtension(ModelExtension):
    """model extension for plugin API test cases"""

    @staticmethod
    def _view_method(plugin_api_context, query_item):
        """a simple view method"""

        log.trace.debug(
            'logged the api context of a simple view method: {0}'.format(
                plugin_api_context
            )
        )
        log.trace.debug(
            'logged the query item of a simple view method: {0}'.format(
                query_item
            )
        )

        return 'true'

    def define_property_types(self):
        """returns a list of custom property regular expressions"""

        property_types = list()
        property_types.append(
            PropertyType(
                property_type_id='tc_story_identifier',
                regex=r'tc[0-9]{2}'
            ),
            PropertyType(
                property_type_id='tc_identifier',
                regex=r'tc[0-9]{2}'
            ),
            PropertyType(
                property_type_id='tc_description',
                regex=r'(?!\d)^[\w_]+'
            ),
            PropertyType(
                property_type_id='tc_type',
                regex=r'positive|negative'
            )
        )

        return property_types

    def define_item_types(self):
        """returns a list of custom item types for plugin API test cases"""

        item_types = list()
        item_types.append(
            ItemType(
                item_type_id='test-module',
                extend_item='software-item',
                tc_story=Property(
                    prop_type_id='tc_story_identifier',
                    prop_description='story identifier',
                    required=True,
                    updatable_rest=False
                ),
                tc_name=Property(
                    prop_type_id='tc_identifier',
                    prop_description='test case identifier',
                    required=True,
                    updatable_rest=False
                ),
                tc_description=Property(
                    prop_type_id='tc_description',
                    prop_description='test case name/description',
                    required=True,
                    updatable_rest=False
                ),
                tc_type=Property(
                    prop_type_id='tc_type',
                    prop_description='type of test case pos|neg',
                    required=True,
                    updatable_rest=False
                ),
                lock_required=Property(
                    prop_type_id='basic_boolean',
                    prop_description='test requires lock task',
                    default='false',
                    required=True,
                    updatable_rest=False
                ),
                plugin_update=Property(
                    prop_type_id='tc_description',
                    prop_description='a callback method to update property ' \
                                     'via a plugin',
                    updatable_plugin=True,
                    updatable_rest=False
                ),
                any_update=Property(
                    prop_type_id='tc_description',
                    prop_description='a callback method to update property ' \
                                     'via a plugin',
                    updatable_plugin=True
                ),
                simple_view=View(
                    prop_type_id='basic_boolean',
                    view_description='logs the context api as debug and ' \
                                     'returns True',
                    callable_method=TestModuleExtension._view_method
                )
            )
        )

        return item_types
