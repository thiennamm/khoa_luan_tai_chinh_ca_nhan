from datetime import date
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from .models import Budget, Category, Transaction, MonthlyCoverage, ForecastResult, ForecastDataVersion
from .budgets import monthly_budgets, budget_progress
from .budget_forms import BudgetForm


class BudgetTests(TestCase):
    def setUp(self):
        self.a = get_user_model().objects.create_user('budget_a', password='qa-only-strong-31')
        self.b = get_user_model().objects.create_user('budget_b', password='qa-only-strong-32')
        self.food = Category.objects.create(user=self.a, name='Ăn <rau> & uống', kind='expense')
        self.other = Category.objects.create(user=self.a, name='Đi lại', kind='expense')
        self.salary = Category.objects.create(user=self.a, name='Lương', kind='income')
        self.foreign = Category.objects.create(user=self.b, name=self.food.name, kind='expense')
        self.month = date(2026, 9, 1)
        self.client.force_login(self.a)

    def budget(self, category=None, amount='100'):
        return Budget.objects.create(user=self.a, month=self.month, category=category, amount=Decimal(amount))

    def spend(self, amount='80', category=None, day=date(2026, 9, 30), user=None, kind='expense'):
        return Transaction.objects.create(user=user or self.a, category=category or self.food,
            kind=kind, amount=Decimal(amount), date=day)

    def payload(self, **kwargs):
        return dict(month='2026-09', category='', amount='100', **kwargs)

    def test_boundary_status_uses_unrounded_decimal_and_clamps_only_drawing(self):
        b=self.budget(amount='100000')
        for spent,status in [('0','within'),('79999','within'),('80000','near'),('99999','near'),('100000','reached'),('135000','over')]:
            with self.subTest(spent=spent):
                r=budget_progress(b,Decimal(spent)); self.assertEqual(r['status'],status)
                self.assertLessEqual(Decimal(r['width']),100)
        r=budget_progress(b,Decimal('135000'))
        self.assertEqual(r['percent'],Decimal('135.00'));self.assertEqual(r['over'],35000)
        self.assertEqual(r['remaining'],0)

    def test_account_month_category_and_no_double_count(self):
        self.budget(amount='1000');self.budget(self.food,'100');self.budget(self.other,'200')
        self.spend('80');self.spend('30',self.other)
        self.spend('900',self.foreign,user=self.b)
        self.spend('500',self.salary,kind='income')
        self.spend('111',day=date(2026,10,1))
        r=monthly_budgets(self.a,self.month)
        self.assertEqual(r['recorded_expense'],Decimal('110'))
        self.assertEqual(r['total_budget']['spent'],Decimal('110'))
        self.assertEqual(sum(x['spent'] for x in r['category_budgets']),Decimal('110'))
        self.assertEqual(r['budget_coverage'],'Chưa xác nhận')

    def test_empty_year_boundary_and_complete_zero(self):
        self.budget();self.assertEqual(monthly_budgets(self.a,self.month)['total_budget']['spent'],0)
        MonthlyCoverage.objects.create(user=self.a,month=self.month,status='complete',confirmed_at=timezone.now())
        self.assertEqual(monthly_budgets(self.a,self.month)['budget_coverage'],'Đã xác nhận đầy đủ')
        self.spend('1',day=date(2025,12,31));self.spend('2',day=date(2026,1,1))
        self.assertEqual(monthly_budgets(self.a,date(2025,12,1))['recorded_expense'],1)
        self.assertEqual(monthly_budgets(self.a,date(2026,1,1))['recorded_expense'],2)

    def test_transaction_update_move_delete_is_live(self):
        self.budget();row=self.spend('80')
        self.assertEqual(monthly_budgets(self.a,self.month)['total_budget']['status'],'near')
        row.amount=Decimal('101');row.save()
        self.assertEqual(monthly_budgets(self.a,self.month)['total_budget']['status'],'over')
        row.date=date(2026,10,1);row.save()
        self.assertEqual(monthly_budgets(self.a,self.month)['total_budget']['spent'],0)
        row.delete();self.assertEqual(monthly_budgets(self.a,date(2026,10,1))['recorded_expense'],0)

    def test_form_rejects_invalid_money_month_category_and_duplicate(self):
        for amount in ['0','-1','1.5','1000000000000000','1,000','NaN','Infinity']:
            with self.subTest(amount=amount):
                data=self.payload();data['amount']=amount
                self.assertFalse(BudgetForm(data,user=self.a).is_valid())
        for category in [self.salary.pk,self.foreign.pk,999999]:
            data=self.payload();data['category']=category
            self.assertFalse(BudgetForm(data,user=self.a).is_valid())
        data=self.payload();data['month']='2026-13'
        self.assertFalse(BudgetForm(data,user=self.a).is_valid())
        self.budget();self.assertFalse(BudgetForm(self.payload(),user=self.a).is_valid())
        self.budget(self.food);data=self.payload();data['category']=self.food.pk
        self.assertFalse(BudgetForm(data,user=self.a).is_valid())

    def test_database_unique_constraints_and_money(self):
        self.budget();self.budget(self.food)
        for cat,amount,month in [(None,'100',self.month),(self.food,'100',self.month),
                (self.other,'0',self.month),(self.other,'-1',self.month),(self.other,'1.5',self.month),
                (self.other,'1000000000000000',self.month),(self.other,'2',date(2026,9,2))]:
            with self.subTest(cat=cat,amount=amount,month=month),self.assertRaises(IntegrityError),transaction.atomic():
                Budget.objects.bulk_create([Budget(user=self.a,category=cat,amount=Decimal(amount),month=month)])
        Budget.objects.create(user=self.b,month=self.month,amount=100)

    def test_database_ownership_kind_and_category_guards(self):
        for category in [self.salary,self.foreign]:
            with self.assertRaises(ValidationError):self.budget(category)
            with self.assertRaises(IntegrityError),transaction.atomic():
                Budget.objects.bulk_create([Budget(user=self.a,month=self.month,category=category,amount=100)])
        b=self.budget(self.food)
        for kwargs in [{'category':self.foreign},{'category':self.salary},{'user':self.b}]:
            with self.assertRaises(IntegrityError),transaction.atomic():Budget.objects.filter(pk=b.pk).update(**kwargs)
        for kwargs in [{'kind':'income'},{'user':self.b}]:
            with self.assertRaises(IntegrityError),transaction.atomic():Category.objects.filter(pk=self.food.pk).update(**kwargs)
        with self.assertRaises(ProtectedError):self.food.delete()
        self.food.kind='income'
        with self.assertRaises(ValidationError):self.food.save()
        self.food.refresh_from_db();self.food.name='Tên mới';self.food.save()
        self.assertEqual(Budget.objects.get(pk=b.pk).category.name,'Tên mới')

    def test_budget_crud_preserves_financial_state_and_owner(self):
        self.spend()
        MonthlyCoverage.objects.create(user=self.a,month=self.month,status='complete',confirmed_at=timezone.now())
        ForecastResult.objects.create(user=self.a,target_month=date(2026,10,1),fingerprint='a'*64,
            history_count=3,history_start=date(2026,7,1),history_end=self.month,method='mean3',estimate='100')
        before=(list(Transaction.objects.values()),list(MonthlyCoverage.objects.values()),
            list(ForecastDataVersion.objects.values()),list(ForecastResult.objects.values()))
        response=self.client.post(reverse('finance:budget_create'),{**self.payload(),'user_id':self.b.pk})
        self.assertEqual(response.status_code,302)
        b=Budget.objects.get();self.assertEqual(b.user,self.a)
        edit=reverse('finance:budget_edit',args=[b.pk]);delete=reverse('finance:budget_delete',args=[b.pk])
        self.assertEqual(self.client.get(delete).status_code,200);self.assertTrue(Budget.objects.exists())
        self.assertEqual(self.client.post(edit,{**self.payload(),'amount':'200'}).status_code,302)
        self.assertEqual(self.client.post(delete).status_code,302)
        after=(list(Transaction.objects.values()),list(MonthlyCoverage.objects.values()),
            list(ForecastDataVersion.objects.values()),list(ForecastResult.objects.values()))
        self.assertEqual(before,after)

    def test_permissions_csrf_scope_and_escaped_names(self):
        b=self.budget(self.food);url=reverse('finance:budget_list')+'?month=2026-09'
        response=self.client.get(url);self.assertContains(response,'Ăn &lt;rau&gt; &amp; uống')
        self.assertContains(self.client.get('/?month=2026-09'),'Ngân sách tháng 09/2026')
        self.client.force_login(self.b)
        self.assertNotContains(self.client.get(url),'Ăn &lt;rau&gt;')
        for action in ['budget_edit','budget_delete']:
            target=reverse('finance:'+action,args=[b.pk])
            self.assertEqual(self.client.get(target).status_code,404)
            self.assertEqual(self.client.post(target,self.payload()).status_code,404)
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.a)
        self.assertEqual(csrf.post(reverse('finance:budget_create'),self.payload()).status_code,403)
        self.client.logout();self.assertEqual(self.client.get(url).status_code,302)

    def test_race_reports_form_error_and_category_protection_is_visible(self):
        with patch('finance.budget_forms.BudgetForm.save',side_effect=IntegrityError):
            response=self.client.post(reverse('finance:budget_create'),self.payload())
        self.assertContains(response,'Không thể lưu:')
        self.budget(self.food)
        response=self.client.get(reverse('finance:category_delete',args=[self.food.pk]))
        self.assertContains(response,'ngân sách nên không thể xóa')
        self.assertNotContains(response,'Xác nhận xóa')
        self.client.post(reverse('finance:category_delete',args=[self.food.pk]))
        self.assertTrue(Category.objects.filter(pk=self.food.pk).exists())
