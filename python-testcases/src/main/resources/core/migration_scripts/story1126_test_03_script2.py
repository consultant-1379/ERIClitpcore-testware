from litp.migration import BaseMigration
from litp.migration.operations import RemoveProperty
from litp.migration.operations import AddProperty

class Migration(BaseMigration):
    version = '1.1.3'
    operations = [
        AddProperty('volume-group', 'prop2', 'null'),
        RemoveProperty('file-system', 'size', '8G'),
    ]
