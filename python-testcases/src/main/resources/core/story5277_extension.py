from litp.core.extension import ModelExtension
from litp.core.model_type import ItemType
from litp.core.model_type import Property


class Story5277Extension(ModelExtension):
    def define_item_types(self):
        return [ItemType("story5277",
                         extend_item="service-base",
                         item_description="Extends service base",
                         name=Property("basic_string",
                                        prop_description="service name",
                                       required=True,
                                       )
                    )
                ]
