from litp.migration import BaseMigration
from litp.migration.operations import RemoveProperty
from litp.migration.operations import RenameProperty
from litp.migration.operations import AddProperty

class Migration(BaseMigration):
    version = '1.1.5'
    operations = [
        AddProperty('file-system', 'prop3', 'item'),
        RemoveProperty('os-profile', 'path', '/profiles'),
        RenameProperty('os-profile', 'name', 'updatedprop'),
      ]
