from litp.migration import BaseMigration
from litp.migration.operations import AddProperty
from litp.migration.operations import RenameProperty
from litp.migration.operations import RemoveProperty

class Migration(BaseMigration):
    version = '1.1.2'
    operations = [ 
    ]
