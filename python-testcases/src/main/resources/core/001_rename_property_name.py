from litp.migration import BaseMigration
from litp.migration.operations import RenameProperty
from litp.migration.operations import AddProperty

class Migration(BaseMigration):
    version = '1.0.2'
    operations = [
        RenameProperty('story6864-node-config', 'name', 'rename'),
        AddProperty('story6864-node-config', 'surname', 'bar')
    ]
