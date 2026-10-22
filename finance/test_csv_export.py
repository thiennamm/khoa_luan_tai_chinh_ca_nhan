import csv
import io
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from django.test import SimpleTestCase
from django.urls import reverse
from .csv_export import protect_text
from .csv_import import inspect_csv, HEADER
from .models import Transaction, Category, MonthlyCoverage, ForecastDataVersion, CsvImportBatch, CsvImportReceipt, ForecastResult
from .tests import FinanceCase


class ExportTextTests(SimpleTestCase):
    def test_formula_controls_unicode_and_leading_space(self):
        for value in ['=1+1','+SUM(1,2)','-1+2','@SUM(1,2)','\t=1+1','\rhello','\nhello',
                      '＝1+1','＋2','－2','＠SUM(1,2)','  =1+1','\ufeff=1+1','\x00=1+1','\u200b=1+1','\x01x']:
            self.assertEqual(protect_text(value),'\t'+value)
        for value in ['', 'Bữa ăn, "cà phê"', 'dòng 1\ndòng 2', '100%_x', 'Tiền điện', "'=1+1"]:
            self.assertEqual(protect_text(value),value)


class CsvExportTests(FinanceCase):
    def setUp(self):
        super().setUp();self.url=reverse('finance:transaction_export')

    def get(self, **extra):
        return self.client.get(self.url, {'month':'2026-10', **extra})

    def parse(self, response):
        raw=b''.join(response.streaming_content)
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf'))
        rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'),newline=''),strict=True))
        self.assertEqual(rows[0],HEADER)
        return raw,rows[1:]

    def test_all_results_not_page_and_totals_order_and_owner(self):
        for i in range(25):
            Transaction.objects.create(user=self.alice,category=self.food,kind='expense',
                date=date(2026,10,31 if i>=12 else 1),amount=Decimal('999999999999999'),description=f'ĐIỆN QA {i:02}')
        Transaction.objects.create(user=self.alice,category=self.salary,kind='income',
            date=date(2026,10,31),amount=Decimal('100'),description='ĐIỆN QA thu')
        params={'q':'điện QA','period':'range','start':'2026-10-01','end':'2026-10-31','page':'2'}
        listing=self.client.get(reverse('finance:transaction_list'),params)
        raw,rows=self.parse(self.get(**params))
        self.assertEqual(len(rows),26)
        expense=sum((Decimal(r[2]) for r in rows if r[1]=='expense'),Decimal('0'))
        income=sum((Decimal(r[2]) for r in rows if r[1]=='income'),Decimal('0'))
        self.assertEqual(expense,listing.context['expense']);self.assertEqual(income,listing.context['income'])
        self.assertEqual(expense,Decimal('24999999999999975'))
        self.assertEqual([r[4] for r in rows],[r.description for r in listing.context['page_obj'].paginator.object_list])
        self.assertNotIn(self.bob_row.description,raw.decode('utf8'))

    def test_combined_kind_category_and_range_uses_list_filter(self):
        target=Transaction.objects.create(user=self.alice,category=self.food,kind='expense',
            date=date(2026,9,30),amount=Decimal('123'),description='Điện & nước')
        params={'period':'range','start':'2026-09-30','end':'2026-09-30','kind':'expense','category':self.food.pk,'q':'ĐIỆN'}
        _,rows=self.parse(self.get(**params))
        self.assertEqual(rows,[['2026-09-30','expense','123',self.food.name,target.description]])
        _,rows=self.parse(self.get(**{**params,'kind':'income'}));self.assertEqual(rows,[])

    def test_headers_filename_and_private_cache(self):
        response=self.get(q='bad\r\nfilename=evil',page=2)
        self.assertEqual(response['Content-Type'],'text/csv; charset=utf-8')
        self.assertEqual(response['Content-Disposition'],'attachment; filename="transactions-202610.csv"')
        self.assertIn('no-store',response['Cache-Control']);self.assertIn('private',response['Cache-Control'])
        self.assertIn('Cookie',response['Vary']);self.assertEqual(response['X-Content-Type-Options'],'nosniff')
        self.parse(response)

    def test_invalid_filters_return_error_html_not_download(self):
        for args in [{'month':'bad'}, {'category':self.bob_category.pk}, {'category':'unknown'},
                     {'period':'bad'}, {'kind':'transfer'}, {'q':'x'*501},
                     {'period':'range','start':'2026-11-01','end':'2026-10-01'},
                     {'period':'range','start':'2026-02-30','end':'2026-03-01'}, {'period':'range'}]:
            response=self.get(**args)
            self.assertEqual(response.status_code,400)
            self.assertNotIn('Content-Disposition',response)
            self.assertContains(response,'Bộ lọc chưa hợp lệ',status_code=400)
            self.assertNotContains(response,self.bob_category.name,status_code=400)
            self.assertNotContains(response,'id="export-csv"',status_code=400)

    def test_empty_header_only_and_valid_default(self):
        raw,rows=self.parse(self.get(q='not-found'))
        self.assertEqual(rows,[])
        self.assertEqual(raw.decode('utf-8-sig'),'date,kind,amount,category,description\r\n')
        with patch('finance.transaction_filters.timezone.localdate',return_value=date(2026,10,21)):
            _,rows=self.parse(self.client.get(self.url))
        self.assertEqual(len(rows),1)

    def test_special_text_quotes_newlines_vietnamese_and_protection_both_columns(self):
        name='=SUM(1,2) "Điện"'
        Category.objects.filter(pk=self.food.pk).update(name=name)
        text='  ＋1+1,"nước"\r\ndòng 2'
        Transaction.objects.filter(pk=self.alice_row.pk).update(description=text)
        raw,rows=self.parse(self.get())
        self.assertEqual(rows[0][3],'\t'+name)
        self.assertEqual(rows[0][4],'\t'+text)
        self.assertIn(b'"\t',raw)
        self.assertEqual(len(rows[0]),5)
        self.alice_row.refresh_from_db();self.food.refresh_from_db()
        self.assertEqual(self.alice_row.description,text);self.assertEqual(self.food.name,name)

    def test_import_does_not_remove_protection_and_protected_category_not_auto_mapped(self):
        Transaction.objects.filter(pk=self.alice_row.pk).update(description='=1+1')
        raw,rows=self.parse(self.get());inspection=inspect_csv(raw,self.alice)
        self.assertTrue(inspection.valid)
        self.assertEqual(inspection.rows[0]['description'],'\t=1+1')
        Category.objects.filter(pk=self.food.pk).update(name='=DANHMUC')
        raw,_=self.parse(self.get());inspection=inspect_csv(raw,self.alice)
        self.assertFalse(inspection.valid)

    def test_button_preserves_filter_not_page_and_disabled_on_invalid(self):
        response=self.client.get(reverse('finance:transaction_list'),{'period':'range','start':'2026-10-01',
            'end':'2026-10-31','q':'điện & nước','kind':'expense','category':self.food.pk,'page':'2'})
        from html import unescape
        import re
        href=unescape(re.search(r'id="export-csv" href="([^"]+)"',response.content.decode()).group(1))
        query=parse_qs(urlsplit(href).query)
        self.assertEqual(query['q'],['điện & nước']);self.assertEqual(query['period'],['range'])
        self.assertNotIn('page',query)
        invalid=self.client.get(reverse('finance:transaction_list'),{'month':'bad'})
        self.assertNotContains(invalid,'id="export-csv"')

    def test_read_only_streaming_and_auth_get_only(self):
        models=[Category,Transaction,MonthlyCoverage,ForecastDataVersion,CsvImportBatch,CsvImportReceipt,ForecastResult]
        before={m.__name__:list(m.objects.values()) for m in models}
        self.parse(self.get(user_id=self.bob.pk))
        self.assertEqual(before,{m.__name__:list(m.objects.values()) for m in models})
        self.assertEqual(self.client.post(self.url).status_code,405)
        self.client.logout();self.assertEqual(self.get().status_code,302)
