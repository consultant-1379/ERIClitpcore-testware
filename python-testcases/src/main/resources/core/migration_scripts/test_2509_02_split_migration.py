from litp.migration import BaseMigration
from litp.migration.operations import BaseOperation


class SplitPropertyOperation(BaseOperation):

    def __init__(self, item_type_id, old_property, new_property1, new_property2):
        self.item_type_id = item_type_id
        self.old_property = old_property
        self.new_property1 = new_property1
        self.new_property2 = new_property2

    def mutate_forward(self, model_manager):
        matched_items = model_manager.find_modelitems(self.item_type_id)
        for item in matched_items:
            if getattr(item, self.old_property) is not None:
                merged_value = getattr(item, self.old_property)
                prop_value1, prop_value2 = merged_value.split('-')
                item.delete_property(self.old_property)
                item.set_property(self.new_property1, prop_value1)
                item.set_property(self.new_property2, prop_value2)

    def mutate_backward(self, model_manager):
        matched_items = model_manager.find_modelitems(self.item_type_id)
        for item in matched_items:
            if (getattr(item, self.new_property1) is not None and
                getattr(item, self.new_property2) is not None):
                prop_value1 = getattr(item, self.new_property1, '')
                prop_value2 = getattr(item, self.new_property2, '')
                merged_value = "%s-%s" % (prop_value1, prop_value2)
                item.delete_property(self.new_property1)
                item.delete_property(self.new_property2)
                item.set_property(self.old_property, merged_value)


class Migration(BaseMigration):
    version = '1.2.2'
    operations = [
        SplitPropertyOperation('package', 'name', 'name', 'version')
    ]
