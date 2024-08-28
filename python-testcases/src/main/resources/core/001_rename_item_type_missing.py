from litp.migration import BaseMigration
from litp.migration.operations import RenameItemType


class Migration(BaseMigration):
    version = '1.0.2'
    operations = [
        # rename the item type that doesn't exist in the code;
        # will fail but litpd will start fine
        RenameItemType('migrations-node-config', 'migrated-node-config')
    ]
