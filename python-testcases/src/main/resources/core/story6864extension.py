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
from litp.core.model_type import Property
from litp.core.model_type import PropertyType


class Story6864Extension(ModelExtension):

    def define_property_types(self):

        # return a new property type test_name with regex validation
        return [
            PropertyType(
                "test_name_story6864", regex=r"^.*$")
        ]

    def define_item_types(self):
        return [
            ItemType(
                "story6864-node-config",
                extend_item="node-config",
                name=Property("test_name_story6864", default="foo"),
            ),
        ]
