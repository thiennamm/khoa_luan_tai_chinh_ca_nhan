from datetime import date
from decimal import Decimal
from django.test import SimpleTestCase
from django.core.exceptions import ValidationError
from django.urls import reverse
from .money import format_vnd
from .money_fields import VNDAmountField, VNDInput
from .forms import TransactionForm
from .budget_forms import BudgetForm
from .recurring_forms import RecurringRuleForm, RecurringConfirmationForm
from .models import Transaction
from .tests import FinanceCase


class MoneyDisplayTests(SimpleTestCase):
    def test_display_zero_negative_large_and_unknown(self):
        for value, expected in [('0','0 VND'), ('50000','50.000 VND'), ('1250000','1.250.000 VND'),
                                ('-50000','-50.000 VND'), ('999999999999999','999.999.999.999.999 VND')]:
            self.assertEqual(format_vnd(Decimal(value)),expected)
        self.assertEqual(format_vnd(None),'—')
        self.assertNotEqual(format_vnd(None),format_vnd(Decimal('0')))

    def test_display_rounding_remains_the_existing_decimal_format(self):
        for value,expected in [('1.5','2 VND'),('2.5','2 VND'),('-2.5','-2 VND'),
                               ('999.49','999 VND'),('999.51','1.000 VND')]:
            self.assertEqual(format_vnd(Decimal(value)),expected)

    def test_field_valid_input_and_decimal_results(self):
        field=VNDAmountField(min_value=Decimal('1'),max_digits=15,decimal_places=0)
        for value,expected in [('50000','50000'),('50.000','50000'),('1.250.000','1250000'),
                               ('999.999.999.999.999','999999999999999'),(' 50.000 ','50000')]:
            result=field.clean(value)
            self.assertIsInstance(result,Decimal)
            self.assertEqual(result,Decimal(expected))

    def test_field_rejects_ambiguous_invalid_and_out_of_range_input(self):
        field=VNDAmountField(min_value=Decimal('1'),max_digits=15,decimal_places=0)
        for value in ['0','-50000','-50.000','+50000','50,000','50.00','1.25.000','1.000,00',
                      '50 000','50.000 VND','5e4','NaN','Infinity','1000000000000000',
                      '1.000.000.000.000.000','0.000','001.000','1.5','','9'*1000]:
            with self.subTest(value=value),self.assertRaises(ValidationError):field.clean(value)

    def test_widget_preserves_invalid_text_and_does_not_round_input(self):
        widget=VNDInput()
        self.assertEqual(widget.format_value(Decimal('50000')),'50.000')
        self.assertEqual(widget.format_value('50000'),'50.000')
        self.assertIsNone(widget.format_value(None))
        for value in ['50.00','50,000',Decimal('1.5')]:
            self.assertEqual(str(widget.format_value(value)),str(value))


class MoneyFormTests(FinanceCase):
    def test_all_money_forms_share_strict_amount_field(self):
        transaction=TransactionForm(self.payload(amount='50.000'),user=self.alice)
        budget=BudgetForm({'month':'2026-10','category':'','amount':'50.000'},user=self.alice)
        rule=RecurringRuleForm({'name':'QA','kind':'expense','category':self.food.pk,'amount':'50.000',
            'due_day':5,'start_month':'2026-10','end_month':''},user=self.alice)
        confirmation=RecurringConfirmationForm(self.payload(amount='50.000',date='2026-01-01'),
            expected_kind='expense',user=self.alice)
        for form in [transaction,budget,rule,confirmation]:
            with self.subTest(form=type(form).__name__):
                self.assertTrue(form.is_valid(),form.errors)
                self.assertEqual(form.cleaned_data['amount'],Decimal('50000'))
                self.assertIn('VND',str(form['amount']))
        self.assertFalse(TransactionForm(self.payload(amount='50.00'),user=self.alice).is_valid())

    def test_no_javascript_post_grouped_amount_saves_exact_value_and_invalid_stays_visible(self):
        url=reverse('finance:transaction_create')
        self.assertEqual(self.client.post(url,self.payload(amount='50.000')).status_code,302)
        row=Transaction.objects.filter(user=self.alice).latest('id')
        self.assertEqual(row.amount,Decimal('50000'))
        before=Transaction.objects.count()
        response=self.client.post(url,self.payload(amount='50,000'))
        self.assertEqual(response.status_code,200)
        self.assertIn('amount',response.context['form'].errors)
        self.assertContains(response,'value="50,000"')
        self.assertEqual(Transaction.objects.count(),before)
