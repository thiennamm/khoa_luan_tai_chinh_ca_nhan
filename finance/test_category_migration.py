from datetime import date
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class CategoryMigrationTests(TransactionTestCase):
    def test_existing_records_survive_with_empty_mapping(self):
        executor = MigrationExecutor(connection)
        previous = [('finance', '0001_initial')]
        current = [('finance', '0002_category_canonical_label')]
        executor.migrate(previous)
        try:
            apps = executor.loader.project_state(previous).apps
            User = apps.get_model('auth', 'User')
            Category = apps.get_model('finance', 'Category')
            Transaction = apps.get_model('finance', 'Transaction')
            user = User.objects.create(username='migration-fixture', password='!')
            category = Category.objects.create(user_id=user.pk, name='Danh mục cũ', kind='expense')
            row = Transaction.objects.create(user_id=user.pk, category_id=category.pk, kind='expense',
                amount=Decimal('123456'), date=date(2026, 10, 1), description='Chỉ trong test DB')
            original = (user.pk, category.pk, row.pk)
            executor = MigrationExecutor(connection)
            executor.migrate(current)
            apps = executor.loader.project_state(current).apps
            updated = apps.get_model('finance', 'Category').objects.get(pk=original[1])
            saved = apps.get_model('finance', 'Transaction').objects.get(pk=original[2])
            self.assertEqual(updated.canonical_label, '')
            self.assertEqual((updated.name, updated.kind, updated.user_id), ('Danh mục cũ', 'expense', original[0]))
            self.assertEqual((saved.amount, saved.description, saved.category_id, saved.user_id),
                (Decimal('123456'), 'Chỉ trong test DB', original[1], original[0]))
            self.assertTrue(apps.get_model('auth', 'User').objects.filter(pk=original[0], username='migration-fixture').exists())
        finally:
            latest = MigrationExecutor(connection)
            latest.migrate(latest.loader.graph.leaf_nodes())
