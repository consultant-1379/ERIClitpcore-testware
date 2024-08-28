from litp.migration import BaseMigration
from litp.migration.operations import RemoveProperty
from litp.migration.operations import RenameProperty
from litp.migration.operations import AddProperty

class Migration(BaseMigration):
    version = '1.1.4'
    operations = [
        AddProperty('network', 'type', 'GSM'),
        RenameProperty('network', 'default_gateway', 'gateway_used'),
      ]
