from datetime import date
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class RecurringMigrationTests(TransactionTestCase):
    def test_existing_financial_and_feedback_rows_unchanged(self):
        previous=[('finance','0010_classificationsuggestion_classificationfeedback')]
        executor=MigrationExecutor(connection)
        executor.migrate(previous)
        try:
            apps=executor.loader.project_state(previous).apps
            user=apps.get_model('auth','User').objects.create(username='recurring-migration-qa',password='!')
            cat=apps.get_model('finance','Category').objects.create(user_id=user.pk,name='QA',kind='expense',canonical_label='Groceries')
            tx=apps.get_model('finance','Transaction').objects.create(user_id=user.pk,category_id=cat.pk,kind='expense',amount=Decimal('10'),date=date(2026,9,1),description='QA only')
            apps.get_model('finance','MonthlyCoverage').objects.create(user_id=user.pk,month=date(2026,9,1),status='complete',confirmed_at=timezone.now())
            apps.get_model('finance','Budget').objects.create(user_id=user.pk,month=date(2026,9,1),amount=Decimal('100'))
            suggestion=apps.get_model('finance','ClassificationSuggestion').objects.create(user_id=user.pk,
                kind='expense',mode='vi',input_digest='0'*64,predicted_label='Groceries',model_name='QA',
                model_sha256='0'*64,seal='0'*64,expires_at=timezone.now(),consumed_at=timezone.now(),saved_transaction_id=tx.pk)
            apps.get_model('finance','ClassificationFeedback').objects.create(user_id=user.pk,transaction_id=tx.pk,
                suggestion_id=suggestion.pk,mode='vi',model_name='QA',model_sha256='0'*64,predicted_label='Groceries',
                final_category_id=cat.pk,final_category_name='QA',final_label='Groceries',applied=False,same_label=True)
            models=[model for model in apps.get_models() if model._meta.app_label in ('finance','auth')]
            before={model._meta.label:list(model.objects.order_by('pk').values()) for model in models}
            executor=MigrationExecutor(connection)
            executor.migrate(executor.loader.graph.leaf_nodes())
            for model in models:
                self.assertEqual(list(model.objects.order_by('pk').values()),before[model._meta.label])
            from .models import RecurringRule,RecurringRevision,RecurringOccurrence,RecurringEvent
            for model in (RecurringRule,RecurringRevision,RecurringOccurrence,RecurringEvent):
                self.assertEqual(model.objects.count(),0)
        finally:
            latest=MigrationExecutor(connection)
            latest.migrate(latest.loader.graph.leaf_nodes())
