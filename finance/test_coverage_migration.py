from datetime import date, timedelta
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class CoverageMigrationTests(TransactionTestCase):
    def test_new_table_does_not_change_accounts_transactions_or_csv(self):
        previous = [('finance', '0003_csvimportbatch_csvimportreceipt')]
        current = [('finance', '0004_monthlycoverage')]
        executor = MigrationExecutor(connection)
        executor.migrate(previous)
        try:
            apps = executor.loader.project_state(previous).apps
            User = apps.get_model('auth', 'User')
            Category = apps.get_model('finance', 'Category')
            Transaction = apps.get_model('finance', 'Transaction')
            Batch = apps.get_model('finance', 'CsvImportBatch')
            Receipt = apps.get_model('finance', 'CsvImportReceipt')
            user = User.objects.create(username='coverage-migration-test', password='!')
            category = Category.objects.create(user_id=user.pk, name='Chỉ trong test DB', kind='expense', canonical_label='Groceries')
            Transaction.objects.create(user_id=user.pk, category_id=category.pk, kind='expense', amount=Decimal('987654321'), date=date(2026, 9, 20), description='Giữ nguyên')
            batch = Batch.objects.create(user_id=user.pk, sha256='a'*64, raw=b'CSV test bytes', category_bindings=[category.pk], expires_at=timezone.now()+timedelta(minutes=30))
            Receipt.objects.create(user_id=user.pk, sha256='b'*64, transaction_count=1)
            models = [('auth','User'),('finance','Category'),('finance','Transaction'),('finance','CsvImportBatch'),('finance','CsvImportReceipt')]
            before = {key:list(apps.get_model(*key).objects.order_by('pk').values()) for key in models}
            executor = MigrationExecutor(connection)
            executor.migrate(current)
            apps = executor.loader.project_state(current).apps
            for key in models:
                self.assertEqual(list(apps.get_model(*key).objects.order_by('pk').values()), before[key])
            self.assertEqual(apps.get_model('finance','MonthlyCoverage').objects.count(),0)
        finally:
            latest = MigrationExecutor(connection)
            latest.migrate(latest.loader.graph.leaf_nodes())
