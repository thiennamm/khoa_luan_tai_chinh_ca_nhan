from datetime import date, timedelta
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from .tests import FinanceCase
from .models import Transaction, SavingsGoal, SavingsEntry, CsvImportBatch
from .recurring_forms import RecurringRuleForm
from . import recurring


class InteractionErrorTests(FinanceCase):
    def test_invalid_transaction_keeps_input_and_links_errors_without_saving(self):
        count = Transaction.objects.count()
        response = self.client.post(reverse('finance:transaction_create'), self.payload(
            amount='50,00', description='Giữ <nội dung> đã nhập'))
        self.assertContains(response, 'Có thông tin cần kiểm tra')
        self.assertContains(response, 'href="#id_amount"')
        self.assertEqual(response.context['form']['amount'].value(), '50,00')
        self.assertEqual(response.context['form']['description'].value(), 'Giữ <nội dung> đã nhập')
        self.assertEqual(Transaction.objects.count(), count)

    def test_common_category_errors_and_initial_get_does_not_claim_error(self):
        url = reverse('finance:category_create')
        self.assertNotContains(self.client.get(url), 'Có thông tin cần kiểm tra')
        response = self.client.post(url, {'name':'Giữ tên', 'kind':'expense', 'canonical_label':'Income'})
        self.assertContains(response, 'href="#id_canonical_label"')
        self.assertEqual(response.context['form']['name'].value(), 'Giữ tên')
        self.assertNotContains(response, self.bob_category.name)

    def test_savings_nonfield_error_keeps_note_and_no_financial_write(self):
        goal = SavingsGoal.objects.create(user=self.alice, name='QA trống', amount=Decimal('100000'), start_date=date(2020,1,1))
        url = reverse('finance:savings_entry_create', args=[goal.pk])
        page = self.client.get(url)
        token = page.context['form']['operation_token'].value()
        count = Transaction.objects.count()
        response = self.client.post(url, {'operation_token':token, 'kind':'withdrawal', 'amount':'1000',
            'date':'2026-09-01', 'note':'Giữ ghi chú QA'})
        self.assertContains(response, 'Có thông tin cần kiểm tra')
        self.assertEqual(response.context['form']['note'].value(), 'Giữ ghi chú QA')
        self.assertFalse(SavingsEntry.objects.exists())
        self.assertEqual(Transaction.objects.count(), count)

    def test_recurring_backend_date_error_is_linked_and_no_transaction(self):
        form = RecurringRuleForm({'name':'QA kỳ', 'kind':'expense', 'amount':'10000', 'category':self.food.pk,
            'due_day':31, 'start_month':timezone.localdate().strftime('%Y-%m'), 'end_month':''}, user=self.alice)
        self.assertTrue(form.is_valid(), form.errors)
        rule = recurring.save_rule(form, self.alice)
        month = timezone.localdate()
        url = reverse('finance:recurring_occurrence',args=[rule.pk,month.year,month.month,'record'])
        count = Transaction.objects.count()
        response = self.client.post(url, {'amount':'10000', 'date':(month+timedelta(days=1)).isoformat(),
            'category':self.food.pk, 'description':'Giữ ghi chú định kỳ'})
        self.assertContains(response, 'href="#id_date"')
        self.assertEqual(response.context['form']['description'].value(), 'Giữ ghi chú định kỳ')
        self.assertEqual(Transaction.objects.count(), count)

    def test_csv_row_errors_have_focus_target_and_do_not_stage_or_import(self):
        raw=f'date,kind,amount,category,description\n2026-10-01,expense,0,{self.food.name},QA\n'.encode()
        count = Transaction.objects.count()
        response = self.client.post(reverse('finance:csv_upload'), {'file':SimpleUploadedFile('qa.csv',raw)})
        self.assertContains(response, 'Cần sửa tệp CSV trước khi nhập')
        self.assertContains(response, 'Dòng 2:')
        self.assertFalse(CsvImportBatch.objects.exists())
        self.assertEqual(Transaction.objects.count(), count)

    def test_invalid_hidden_token_is_explained_without_echoing_it_in_summary(self):
        response = self.client.post(reverse('finance:savings_create'), {'operation_token':'qa-invalid-token' * 150,
            'name':'QA', 'amount':'10000', 'start_date':'2026-09-01','due_date':'','note':''})
        self.assertContains(response, 'Phiên biểu mẫu không hợp lệ')
        summary = response.content.decode().split('data-error-summary',1)[1].split('</section>',1)[0]
        self.assertNotIn('qa-invalid-token',summary)
