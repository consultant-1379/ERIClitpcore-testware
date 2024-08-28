from litp.migration import BaseMigration
from litp.migration.operations import UpdateCollectionType


class Migration(BaseMigration):
    version = '1.0.2'
    operations = [
        # this should be successful
        UpdateCollectionType(
            'migrations-node-config', 'migration_items_collection',
            'migration-config', 'node-config'
        ),
        # this should fail with error message but litpd will not fail to start
        UpdateCollectionType(
            'migrations-node-config', 'collection_not_empty',
            'migration-config', 'software-item'
        ),
        # this should be successful because it is an empty collection
        UpdateCollectionType(
            'migrations-node-config', 'collection_empty',
            'migration-config', 'software-item'
        )
    ]
