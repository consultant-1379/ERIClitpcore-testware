##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from litp.core.model_type import ItemType, Property, PropertyType
from litp.core.extension import ModelExtension

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story200916Extension(ModelExtension):
    """
    Story200916 Model Extension
    """

    def define_property_types(self):
        property_types = []
        property_types.append(PropertyType("configuration_type",
                                          regex="^[1-9][0-9]{0,}G$"),)
        property_types.append(PropertyType("non_configuration_type",
                                          regex="^[1-9][0-9]{0,}G$"),)
        return property_types

    def define_item_types(self):
        item_types = []
        item_types.append(
            ItemType("torf-200916-item-type",
                    extend_item="software-item",
                    item_description="TORF-200916 item type",
                    configuration_property=Property(
                            "configuration_type",
                            prop_description="Example configuration property",
                            required=True),
                    non_configuration_property=Property(
                            "non_configuration_type",
                            prop_description="Example non configuration prop",
                            default="10G", configuration=False),
           )
        )
        return item_types
