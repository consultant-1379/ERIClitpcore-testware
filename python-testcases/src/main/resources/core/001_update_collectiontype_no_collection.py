from litp.migration import BaseMigration
from litp.migration.operations import UpdateCollectionType


class Migration(BaseMigration):
    version = '1.0.2'
    operations = [
        # add a collection that doesn't exist in the code;
        # will fail but litpd will start fine
        UpdateCollectionType(
            'migrations-node-config', 'collection_items_missing_no_appear',
            'migration-config', 'migrated-config'
        )
    ]
