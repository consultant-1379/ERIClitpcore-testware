from litp.core.model_type import ItemType, Property
from litp.core.extension import ModelExtension

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story3330Extension(ModelExtension):
    """Story3330 Model extension
       We define one extension, a type 'story3330'
       Usage - litp create -p /software-item/xyz -t story3330
    """

    def define_item_types(self):
        return [
            ItemType(
                'story3330',
                extend_item='software-item',
                name=Property('any_string'),
            )
        ]
