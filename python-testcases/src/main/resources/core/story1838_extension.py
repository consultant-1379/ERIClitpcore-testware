from litp.core.extension import ModelExtension
from litp.core.model_type import ItemType
from litp.core.model_type import Property
from litp.core.model_type import PropertyType


class Story1838Extension(ModelExtension):

    def define_property_types(self):

        # return a new property type test_name with regex validation
        return [
            PropertyType(
                    "test_name", regex="test_0[1-9]|test_1[0-1]|test_updated")
        ]

    def define_item_types(self):

        # return a new item type story1838 that uses property name of property
        # type test_name above and second_plugin boolean with default set to
        # false
        return [
            ItemType(
                "story1838",
                extend_item="software-item",
                name=Property("test_name"),
                second_plugin=Property('basic_boolean',
                                        default="false")
            ),
        ]
