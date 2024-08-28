##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################
'''Story10575 Exrension'''
from litp.core.model_type import ItemType, Property, PropertyType
from litp.core.extension import ModelExtension

#from litp.core.litp_logging import LitpLogger
#log = LitpLogger()


class Story10575Extension(ModelExtension):
    """
    Story10575 Model Extension
    """

    def define_property_types(self):
        property_types = []
        property_types.append(PropertyType("example_property_type",
                                           regex="^[1-9][0-9]{0,}G$"),)
        return property_types

    def define_item_types(self):
        return [
            ItemType("story-10575a",
                     extend_item="software-item",
                     item_description="Example item type",
                     name=Property(
                         "basic_string", prop_description="Name of item",
                         required=True),
                     size=Property(
                         "example_property_type",
                         prop_description="Size of item",
                         default="10G"),
                     deconfigure=Property(
                         "any_string",
                         prop_description="deconfigure tasks generated",
                         default="false"),
                     multipleconfig=Property(
                         "any_string",
                         prop_description="generate multiple configTasks",
                         default="false"),
                     packagename=Property(
                         "any_string",
                         prop_description="name of package to install"),
                     failplan=Property(
                         "any_string",
                         prop_description="fail deconfigure task",
                         default="false"),
                     failphase=Property(
                         "any_string",
                         prop_description="fail deconfigure phase",
                         default="false"),
                     wait=Property(
                         "any_string",
                         prop_description="allows puppet manifests to be read",
                         default="false"
                     )
            ),
            ItemType(
                "depend-story-10575",
                extend_item="software-item",
                name=Property("any_string"),
            ),
            ItemType(
                "depend2-story-10575",
                extend_item="software-item",
                name=Property("any_string")
            )
        ]
