from litp.core.model_type import ItemType, Property
from litp.core.extension import ModelExtension

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story2682Extension(ModelExtension):

    def define_item_types(self):
        return [
            ItemType(
                'story2682',
                extend_item='software-item',
                name=Property('any_string'),
                callback_task_true=Property('basic_boolean'),
                config_task_true=Property('basic_boolean'),
                no_task_true=Property('basic_boolean')
                    )
                ]
