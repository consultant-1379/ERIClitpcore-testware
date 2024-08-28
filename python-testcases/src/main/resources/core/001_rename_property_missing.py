from litp.migration import BaseMigration
from litp.migration.operations import RenameProperty


class Migration(BaseMigration):
    version = '1.0.2'
    operations = [
        # rename property that doesn't exist in the code;
        # will fail and litp will not start
        RenameProperty('migrations-node-config', 'name', 'no_name')
    ]
