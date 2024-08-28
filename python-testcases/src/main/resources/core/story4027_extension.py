from litp.core.extension import ModelExtension
from litp.core.model_type import ItemType
from litp.core.model_type import PropertyType
from litp.core.model_type import Property
from litp.core.model_type import Collection

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story4027Extension(ModelExtension):

    def define_property_types(self):
        return [
            PropertyType("4027_collection", regex=r'test_0[1-3]'),
            PropertyType("4027_name", regex=r'test_0[1-3]')
        ]

    def define_item_types(self):
        return [
            ItemType(
                "story4027-items",
                extend_item="software-item",
                story4027_items=Collection("story4027"),
                name=Property("4027_collection", required=True),
                updatable=Property(
                    "basic_boolean",
                    default="true",
                    required=True,
                    updatable_plugin=True,
                    updatable_rest=False
                )

            ),
            ItemType(
                "story4027",
                extend_item="software-item",
                name=Property("4027_name", required=True),
                updatable=Property(
                    "basic_boolean",
                    default="true",
                    required=True,
                    updatable_plugin=True,
                    updatable_rest=False
                )

            )
        ]
