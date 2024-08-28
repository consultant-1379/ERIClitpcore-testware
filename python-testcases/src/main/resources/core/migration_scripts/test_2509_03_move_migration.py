from litp.migration import BaseMigration
from litp.migration.operations import BaseOperation

class MovePropertyOperation(BaseOperation):

    def __init__(self, old_item_type_id, new_item_type_id, property_name):
        self.old_item_type_id = old_item_type_id
        self.new_item_type_id = new_item_type_id
        self.property_name = property_name

    def mutate_forward(self, model_manager):
        old_matched_items = model_manager.find_modelitems(self.old_item_type_id)
        new_matched_items = model_manager.find_modelitems(self.new_item_type_id)
        for old_item in old_matched_items:
            for new_item in new_matched_items:
                if getattr(old_item, "repository") is not None and \
                   getattr(old_item, "repository") == getattr(new_item, "name"):
                    if getattr(old_item, self.property_name) is not None:
                        prop_value = getattr(old_item, self.property_name)
                        old_item.delete_property(self.property_name)
                        new_item.set_property(self.property_name, prop_value)

    def mutate_backward(self, model_manager):
        old_matched_items = model_manager.find_modelitems(self.old_item_type_id)
        new_matched_items = model_manager.find_modelitems(self.new_item_type_id)
        for old_item in old_matched_items:
            for new_item in new_matched_items:
                if getattr(old_item, "repository") is not None and \
                   getattr(old_item, "repository") == getattr(new_item, "name"):
                    if getattr(new_item, self.property_name) is not None:
                        prop_value = getattr(new_item, self.property_name)
                        new_item.delete_property(self.property_name)
                        old_item.set_property(self.property_name, prop_value)

class Migration(BaseMigration):
    version = '1.2.2'
    operations = [ 
        MovePropertyOperation('package', 'yum-repository', 'config')
    ]
