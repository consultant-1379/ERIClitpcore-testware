from litp.core.extension import ModelExtension
from litp.core.model_type import ItemType
from litp.core.model_type import Property


class Story5649Extension(ModelExtension):

    def define_item_types(self):
        return [
            ItemType(
                "story5649",
                extend_item="software-item",
                name=Property("basic_string"),
            ),
        ]
