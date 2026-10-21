from datetime import date
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class ForecastMigrationTests(TransactionTestCase):
    def test_preserves_old_rows_and_does_not_create_forecasts_or_versions(self):
        previous=[('finance','0004_monthlycoverage')]
        current=[('finance','0005_forecastdataversion_forecastresult')]
        executor=MigrationExecutor(connection)
        executor.migrate(previous)
        try:
            apps=executor.loader.project_state(previous).apps
            user=apps.get_model('auth','User').objects.create(username='forecast-migration-test',password='!')
            category=apps.get_model('finance','Category').objects.create(user_id=user.pk,name='Test only',kind='expense')
            apps.get_model('finance','Transaction').objects.create(user_id=user.pk,category_id=category.pk,kind='expense',amount=Decimal('123456'),date=date(2026,9,1),description='Test only')
            apps.get_model('finance','MonthlyCoverage').objects.create(user_id=user.pk,month=date(2026,9,1),status='complete',confirmed_at=timezone.now())
            keys=[('auth','User'),('finance','Category'),('finance','Transaction'),('finance','MonthlyCoverage'),('finance','CsvImportBatch'),('finance','CsvImportReceipt')]
            before={key:list(apps.get_model(*key).objects.order_by('pk').values()) for key in keys}
            executor=MigrationExecutor(connection)
            executor.migrate(current)
            apps=executor.loader.project_state(current).apps
            for key in keys:
                self.assertEqual(list(apps.get_model(*key).objects.order_by('pk').values()),before[key])
            self.assertEqual(apps.get_model('finance','ForecastResult').objects.count(),0)
            self.assertEqual(apps.get_model('finance','ForecastDataVersion').objects.count(),0)
        finally:
            latest=MigrationExecutor(connection)
            latest.migrate(latest.loader.graph.leaf_nodes())
