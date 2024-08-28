from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
from litp.migration.operations import RenameProperty

class Migration(BaseMigration):
    version = '1.0.2'
    operations = [
        AddProperty('story6864-node-config', 'surname', 'bar'),
        RenameProperty('story6864-node-config', 'name', 'rename')
    ]
