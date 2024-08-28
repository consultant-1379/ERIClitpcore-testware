from litp.core.model_type import ItemType, Property
from litp.core.extension import ModelExtension

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story5508Extension(ModelExtension):
    def define_item_types(self):
        return [
            ItemType(
                'story5508',
                extend_item='software-item',
                item_description='Item type extension LITPCDS-5508',
                name=Property(
                    'basic_string',
                    prop_description='name',
                    required=True
                ),
                ensure=Property(
                    'basic_string',
                    prop_description='updated via CallbackTask()',
                    default='absent',
                    required=True,
                    updatable_plugin=True,
                    updatable_rest=False
                )
            )
        ]
