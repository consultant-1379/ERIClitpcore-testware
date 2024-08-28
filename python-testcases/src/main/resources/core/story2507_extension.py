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


class Story2507Extension(ModelExtension):

    def define_item_types(self):
        return [
            ItemType(
                "story2507-software-item",
                extend_item="software-item",
                name=Property("any_string", default=""),
                version=Property("any_string", default=""),
            ),
        ]
