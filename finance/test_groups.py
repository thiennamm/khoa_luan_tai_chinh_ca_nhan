from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from queue import Queue
from threading import Thread, Barrier
from unittest import skipUnless
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, close_old_connections, transaction, IntegrityError, OperationalError
from django.db.models.deletion import ProtectedError, RestrictedError
from django.test import TestCase, TransactionTestCase, Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from . import groups, wallets
from .models import (Transaction, Category, Wallet, MonthlyCoverage, ForecastDataVersion,
    ClassificationFeedback, WalletTransfer, GroupMember, GroupShare, GroupExpense,
    ExpenseGroup, GroupSettlement, GroupAllocation, GroupWalletPosting, GroupOperation)
from .services import monthly_totals
from .budgets import monthly_budgets
from .group_forms import ExpenseForm

DAY=date(2026,10,10)


class GroupFixture:
    def setUp(self):
        super().setUp()
        self.clock=patch('finance.wallets.today',return_value=date(2026,11,9));self.clock.start();self.addCleanup(self.clock.stop)
        self.group_clock=patch('finance.groups.today',return_value=date(2026,11,9));self.group_clock.start();self.addCleanup(self.group_clock.stop)
        User=get_user_model()
        self.a=User.objects.create_user('group-a');self.b=User.objects.create_user('group-b');self.c=User.objects.create_user('group-c')
        self.cat={u.pk:Category.objects.create(user=u,name='Chi riêng',kind='expense') for u in (self.a,self.b,self.c)}
        self.wa=Wallet.objects.create(user=self.a,name='Ví A',kind='cash',opening_balance=1000000,start_date=date(2026,1,1))
        self.wb=Wallet.objects.create(user=self.b,name='Ví B',kind='bank',opening_balance=500000,start_date=date(2026,1,1))
        self.wc=Wallet.objects.create(user=self.c,name='Ví C',kind='bank',opening_balance=500000,start_date=date(2026,1,1))
        self.gid=groups.create_group(self.a,self.token(self.a,'create'),'Nhóm QA <script>')
        self.ma=GroupMember.objects.get(group_id=self.gid,user=self.a)
        self.mb=self.join(self.b);self.mc=self.join(self.c)

    def token(self,user,action,target=0,gid=None):
        return groups.issue(user,action,getattr(self,'gid',0) if gid is None else gid,target)

    def join(self,user):
        pk=groups.invite(self.a,self.token(self.a,'invite'),self.gid,user.username)
        groups.membership_action(user,self.token(user,'join',pk),self.gid,pk,'join')
        return GroupMember.objects.get(pk=pk)

    def expense(self,total=300000,members=None,**kw):
        data={'amount':Decimal(total),'date':DAY,'description':'Ăn nhóm QA <b>mô phỏng</b>',
              'method':'equal','members':members or [self.ma.pk,self.mb.pk,self.mc.pk],**kw}
        return groups.create_expense(self.a,self.token(self.a,'expense'),self.gid,data)

    def accept(self,expense_id,user,member=None):
        s=GroupShare.objects.get(expense_id=expense_id,member__user=user)
        groups.respond_share(user,self.token(user,'share_accept',s.pk),self.gid,s.pk,True,self.cat[user.pk].pk if s.amount else None)
        s.refresh_from_db();return s

    def debt(self):
        expense=self.expense()
        return expense,self.accept(expense,self.b)

    def propose(self,share,amount=40000,user=None,token=None):
        user=user or self.b
        return groups.propose_settlement(user,token or self.token(user,'settlement'),self.gid,
            {'amount':Decimal(amount),'date':DAY,'shares':[share.pk]})

    def confirm(self,pk):
        return groups.settlement_action(self.a,self.token(self.a,'settlement_confirm',pk),self.gid,pk,'confirm')

    def post(self,user,source,side,wallet):
        return groups.post_wallet(user,self.token(user,'post_'+side,source),self.gid,source,side,wallet.pk)


class GroupTests(GroupFixture,TestCase):
    def test_equal_rounding_stable_and_one_dong(self):
        for ids in [[3,1,2],[1,2,3]]:
            self.assertEqual(groups.split(100000,ids,'equal'),{1:33334,2:33333,3:33333})
            self.assertEqual(groups.split(1,ids,'equal'),{1:1,2:0,3:0})
        self.assertEqual(groups.split(Decimal('999999999999999'),[1,2],'equal'),{1:500000000000000,2:499999999999999})

    def test_invalid_money_and_exact_totals(self):
        for value in [0,-1,'0.5','NaN','Infinity',1000000000000000,1.0,True]:
            with self.subTest(value=value),self.assertRaises(ValidationError):groups.amount(value)
        for exact in [{1:1,2:1},{1:100000},{1:-1,2:100001}]:
            with self.assertRaises(ValidationError):groups.split(100000,[1,2],'exact',exact)
        self.assertEqual(groups.split(100000,[1,2],'exact',{1:0,2:100000}),{1:0,2:100000})
        with self.assertRaises(ValidationError):groups.split(1,[1,1],'equal')

    def test_invitation_requires_acceptance_and_owner(self):
        outsider=get_user_model().objects.create_user('invite-qa')
        mid=groups.invite(self.a,self.token(self.a,'invite'),self.gid,outsider.username)
        self.client.force_login(outsider)
        self.assertEqual(self.client.get(reverse('finance:group_detail',args=[self.gid])).status_code,404)
        with self.assertRaises(ValidationError):groups.invite(self.b,self.token(self.b,'invite'),self.gid,outsider.username)
        groups.membership_action(outsider,self.token(outsider,'join',mid),self.gid,mid,'join')
        self.assertEqual(self.client.get(reverse('finance:group_detail',args=[self.gid])).status_code,200)

    def test_revoke_prevents_old_invitation_and_preserves_member(self):
        outsider=get_user_model().objects.create_user('invite-revoke')
        mid=groups.invite(self.a,self.token(self.a,'invite'),self.gid,outsider.username)
        old=self.token(outsider,'join',mid)
        groups.membership_action(self.a,self.token(self.a,'revoke',mid),self.gid,mid,'revoke')
        with self.assertRaises(ValidationError):groups.membership_action(outsider,old,self.gid,mid,'join')
        self.assertEqual(GroupMember.objects.get(pk=mid).status,'revoked')
        groups.invite(self.a,self.token(self.a,'invite'),self.gid,outsider.username)
        with self.assertRaises(ValidationError):groups.membership_action(outsider,old,self.gid,mid,'join')
        groups.membership_action(outsider,self.token(outsider,'join',mid),self.gid,mid,'join')
        self.assertEqual(GroupMember.objects.get(pk=mid).status,'active')

    def test_pending_and_rejected_do_not_touch_private_book(self):
        coverage=MonthlyCoverage.objects.create(user=self.b,month=date(2026,10,1),status='complete',confirmed_at=timezone.now())
        before_version=ForecastDataVersion.objects.get(user=self.b).version
        eid=self.expense();share=GroupShare.objects.get(expense_id=eid,member=self.mb)
        self.assertEqual(groups.obligations(self.gid),[])
        self.assertFalse(Transaction.objects.exists())
        self.assertEqual(ForecastDataVersion.objects.get(user=self.b).version,before_version)
        groups.respond_share(self.b,self.token(self.b,'share_reject',share.pk),self.gid,share.pk,False)
        coverage.refresh_from_db();self.assertEqual(coverage.status,'complete')
        self.assertEqual(wallets.balances(self.b)['wallet_total'],500000)
        self.assertFalse(ClassificationFeedback.objects.exists())

    def test_accept_only_owner_private_category_and_coverage(self):
        coverage=MonthlyCoverage.objects.create(user=self.b,month=date(2026,10,1),status='complete',confirmed_at=timezone.now())
        eid=self.expense();share=GroupShare.objects.get(expense_id=eid,member=self.mb)
        with self.assertRaises(ValidationError):groups.respond_share(self.a,self.token(self.a,'share_accept',share.pk),self.gid,share.pk,True,self.cat[self.a.pk].pk)
        with self.assertRaises(ValidationError):groups.respond_share(self.b,self.token(self.b,'share_accept',share.pk),self.gid,share.pk,True,self.cat[self.a.pk].pk)
        self.accept(eid,self.b)
        row=Transaction.objects.get(user=self.b)
        self.assertEqual((row.amount,row.wallet_id,row.date),(Decimal(100000),None,DAY))
        self.assertFalse(Transaction.objects.filter(user=self.a).exists())
        coverage.refresh_from_db();self.assertEqual(coverage.status,'unknown');self.assertIsNone(coverage.confirmed_at)
        self.assertEqual(groups.obligations(self.gid)[0]['remaining'],100000)
        self.assertEqual(monthly_budgets(self.b,date(2026,10,1))['recorded_expense'],100000)
        self.assertTrue(ForecastDataVersion.objects.filter(user=self.b).exists())

    def test_zero_share_accept_creates_no_zero_transaction(self):
        eid=self.expense(1);self.accept(eid,self.c)
        self.assertFalse(Transaction.objects.filter(user=self.c).exists())
        self.assertEqual(groups.obligations(self.gid),[])

    def test_payer_own_share_never_owes_self(self):
        eid=self.expense();self.accept(eid,self.a)
        self.assertEqual(Transaction.objects.get(user=self.a).amount,100000)
        self.assertEqual(groups.obligations(self.gid),[])

    def test_share_accept_receipt_repeat_and_modified_payload(self):
        eid=self.expense();share=GroupShare.objects.get(expense_id=eid,member=self.mb)
        token=self.token(self.b,'share_accept',share.pk)
        for _ in range(2):groups.respond_share(self.b,token,self.gid,share.pk,True,self.cat[self.b.pk].pk)
        self.assertEqual(Transaction.objects.filter(user=self.b).count(),1)
        with self.assertRaises(ValidationError):groups.respond_share(self.b,token,self.gid,share.pk,True,self.cat[self.a.pk].pk)

    def test_share_rolls_back_transaction_and_coverage_on_link_error(self):
        eid=self.expense();share=GroupShare.objects.get(expense_id=eid,member=self.mb)
        before=GroupOperation.objects.count()
        with patch('finance.groups._update',side_effect=ValidationError('QA rollback')):
            with self.assertRaises(ValidationError):self.accept(eid,self.b)
        self.assertFalse(Transaction.objects.exists());self.assertFalse(ForecastDataVersion.objects.exists())
        self.assertEqual(GroupOperation.objects.count(),before)
        share.refresh_from_db();self.assertEqual(share.status,'pending')

    def test_pending_reservation_prevents_total_over_debt(self):
        _,share=self.debt();first=self.propose(share,60000)
        state=groups.obligations(self.gid)[0]
        self.assertEqual((state['remaining'],state['reserved'],state['available']),(100000,60000,40000))
        with self.assertRaises(ValidationError):self.propose(share,50000)
        self.confirm(first)
        state=groups.obligations(self.gid)[0]
        self.assertEqual((state['remaining'],state['reserved'],state['available']),(40000,0,40000))

    def test_cancel_reject_expire_release_reservations_without_cash(self):
        _,share=self.debt()
        for action,user in [('cancel',self.b),('reject',self.a)]:
            pk=self.propose(share,100000)
            groups.settlement_action(user,self.token(user,'settlement_'+action,pk),self.gid,pk,action)
            self.assertEqual(groups.obligations(self.gid)[0]['available'],100000)
        pk=self.propose(share,100000)
        with patch('finance.groups.timezone.now',return_value=timezone.now()+timedelta(days=8)):
            self.assertEqual(groups.obligations(self.gid)[0]['available'],100000)
            with self.assertRaises(ValidationError):self.confirm(pk)
        self.assertEqual(GroupWalletPosting.objects.count(),0)

    def test_only_receiver_confirms_and_confirm_is_idempotent(self):
        _,share=self.debt();pk=self.propose(share)
        with self.assertRaises(ValidationError):groups.settlement_action(self.b,self.token(self.b,'settlement_confirm',pk),self.gid,pk,'confirm')
        token=self.token(self.a,'settlement_confirm',pk)
        for _ in range(2):groups.settlement_action(self.a,token,self.gid,pk,'confirm')
        self.assertEqual(GroupSettlement.objects.filter(status='confirmed').count(),1)
        self.assertEqual(groups.obligations(self.gid)[0]['remaining'],60000)
        self.assertEqual(Transaction.objects.count(),1);self.assertFalse(GroupWalletPosting.objects.exists())

    def test_settlement_date_and_foreign_debt_rejected(self):
        _,share=self.debt()
        for user,day in [(self.c,DAY),(self.b,date(2026,10,9)),(self.b,date(2026,11,10))]:
            with self.assertRaises(ValidationError):groups.propose_settlement(user,self.token(user,'settlement'),self.gid,
                {'amount':1,'date':day,'shares':[share.pk]})

    def test_full_example_cash_consumption_and_repayments_do_not_double_count(self):
        eid=self.expense()
        shares={u.pk:self.accept(eid,u) for u in (self.a,self.b,self.c)}
        self.post(self.a,eid,'bill',self.wa)
        self.assertEqual(wallets.balances(self.a)['wallet_total'],700000)
        for user,wallet,value in [(self.b,self.wb,40000),(self.b,self.wb,60000),(self.c,self.wc,100000)]:
            pk=self.propose(shares[user.pk],value,user=user);self.confirm(pk)
            self.post(user,pk,'pay',wallet);self.post(self.a,pk,'receive',self.wa)
        self.assertEqual([wallets.balances(u)['wallet_total'] for u in (self.a,self.b,self.c)],[900000,400000,400000])
        for user in (self.a,self.b,self.c):
            totals=monthly_totals(user,date(2026,10,1),date(2026,11,1))
            self.assertEqual((totals['expense'],totals['income']),(100000,0))
            self.assertEqual(wallets.balances(user)['unknown']['expense'],0)
        self.assertTrue(all(r['remaining']==0 for r in groups.obligations(self.gid)))
        self.assertEqual(Transaction.objects.count(),3);self.assertEqual(WalletTransfer.objects.count(),0)
        self.assertFalse(ClassificationFeedback.objects.exists())

    def test_posting_requires_correct_side_wallet_and_confirmed_source(self):
        eid,share=self.debt();pk=self.propose(share)
        with self.assertRaises(ValidationError):self.post(self.b,pk,'pay',self.wb)
        with self.assertRaises(ValidationError):self.post(self.b,eid,'bill',self.wb)
        self.confirm(pk)
        with self.assertRaises(ValidationError):self.post(self.b,pk,'pay',self.wa)
        before=ForecastDataVersion.objects.get(user=self.b).version
        self.post(self.b,pk,'pay',self.wb)
        self.assertEqual(ForecastDataVersion.objects.get(user=self.b).version,before)
        self.assertEqual(Transaction.objects.count(),1)

    def test_posting_once_and_private_other_side_stays_unassigned(self):
        _,share=self.debt();pk=self.propose(share);self.confirm(pk)
        token=self.token(self.b,'post_pay',pk)
        for _ in range(2):groups.post_wallet(self.b,token,self.gid,pk,'pay',self.wb.pk)
        self.post(self.b,pk,'pay',self.wb) # new token, same source still one posting
        self.assertEqual(GroupWalletPosting.objects.count(),1)
        self.assertEqual(wallets.balances(self.b)['wallet_total'],460000)
        self.assertEqual(wallets.balances(self.a)['group_cash_unassigned']['in'],40000)
        self.assertEqual(wallets.balances(self.a)['wallet_total'],1000000)

    def test_posting_rollback_and_archived_wallet(self):
        eid=self.expense()
        with patch('finance.models.WalletQuerySet.update',side_effect=ValidationError('rollback')):
            with self.assertRaises(ValidationError):self.post(self.a,eid,'bill',self.wa)
        self.assertFalse(GroupWalletPosting.objects.exists())
        self.wa.refresh_from_db();self.assertFalse(self.wa.opening_locked)
        self.wa.archived=True;self.wa.save()
        with self.assertRaises(ValidationError):self.post(self.a,eid,'bill',self.wa)

    def test_wallet_date_opening_and_archive_history(self):
        eid=self.expense();self.post(self.a,eid,'bill',self.wa)
        self.wa.refresh_from_db();self.assertTrue(self.wa.opening_locked)
        self.wa.opening_balance=42
        with self.assertRaises(ValidationError):self.wa.save()
        self.wa.refresh_from_db();self.wa.archived=True;self.wa.save()
        result=wallets.balances(self.a)
        self.assertEqual(result['wallet_total'],0);self.assertEqual(result['wallet_rows'][0]['balance'],700000)
        with self.assertRaises(ValidationError):self.wa.delete()

    def test_linked_transaction_guards_instance_queryset_delete_but_category_edit_allowed(self):
        eid=self.expense();share=self.accept(eid,self.b);row=share.transaction
        row.amount=999
        with self.assertRaises(ValidationError):row.save()
        with self.assertRaises(ValidationError):Transaction.objects.filter(pk=row.pk).update(wallet=self.wb)
        with self.assertRaises(ProtectedError):row.delete()
        row.refresh_from_db();row.description='Ghi chú riêng';row.save()
        self.assertEqual(Transaction.objects.get(pk=row.pk).description,'Ghi chú riêng')
        self.client.force_login(self.b)
        response=self.client.post(reverse('finance:transaction_delete',args=[row.pk]))
        self.assertEqual(response.status_code,400);self.assertTrue(Transaction.objects.filter(pk=row.pk).exists())

    def test_void_only_before_acceptance_and_posting(self):
        eid=self.expense();groups.void_expense(self.a,self.token(self.a,'void',eid),self.gid,eid)
        self.assertTrue(GroupExpense.objects.get(pk=eid).voided)
        with self.assertRaises(ValidationError):self.accept(eid,self.b)
        eid=self.expense();self.accept(eid,self.b)
        with self.assertRaises(ValidationError):groups.void_expense(self.a,self.token(self.a,'void',eid),self.gid,eid)
        with self.assertRaises(ValidationError):GroupExpense.objects.filter(pk=eid).update(amount=1)
        with self.assertRaises(ValidationError):GroupExpense.objects.get(pk=eid).delete()

    def test_leave_reinvite_preserves_financial_history(self):
        eid,share=self.debt()
        with self.assertRaises(ValidationError):groups.membership_action(self.b,self.token(self.b,'leave',self.mb.pk),self.gid,self.mb.pk,'leave')
        pk=self.propose(share,100000);self.confirm(pk)
        groups.membership_action(self.b,self.token(self.b,'leave',self.mb.pk),self.gid,self.mb.pk,'leave')
        self.assertEqual(GroupMember.objects.get(pk=self.mb.pk).status,'left')
        self.assertTrue(GroupShare.objects.filter(pk=share.pk,status='accepted').exists())
        mid=groups.invite(self.a,self.token(self.a,'invite'),self.gid,self.b.username)
        self.assertEqual(mid,self.mb.pk)
        groups.membership_action(self.b,self.token(self.b,'join',mid),self.gid,mid,'join')
        self.assertEqual(GroupSettlement.objects.get(pk=pk).status,'confirmed')

    def test_owner_cannot_leave_and_account_deletion_protected(self):
        with self.assertRaises(ValidationError):groups.membership_action(self.a,self.token(self.a,'leave',self.ma.pk),self.gid,self.ma.pk,'leave')
        with self.assertRaises(ProtectedError):self.a.delete()

    def test_archive_read_only_and_own_receipts_do_not_bypass(self):
        groups.archive_group(self.a,self.token(self.a,'archive'),self.gid)
        with self.assertRaises(ValidationError):self.expense()
        self.assertTrue(ExpenseGroup.objects.get(pk=self.gid).archived)

    def test_rename_owner_only_and_keeps_snapshots(self):
        eid=self.expense()
        with self.assertRaises(ValidationError):groups.rename_group(self.b,self.token(self.b,'rename'),self.gid,'Tên khác')
        groups.rename_group(self.a,self.token(self.a,'rename'),self.gid,'Nhóm mới QA')
        self.assertEqual(ExpenseGroup.objects.get(pk=self.gid).name,'Nhóm mới QA')
        self.assertEqual(GroupExpense.objects.get(pk=eid).description,'Ăn nhóm QA <b>mô phỏng</b>')

    def test_private_cash_assignment_after_archive_or_leaving_does_not_reopen_group(self):
        eid,share=self.debt();pk=self.propose(share,100000);self.confirm(pk)
        for s in GroupShare.objects.filter(expense_id=eid,status='pending'):
            groups.respond_share(s.member.user,self.token(s.member.user,'share_reject',s.pk),self.gid,s.pk,False)
        groups.membership_action(self.b,self.token(self.b,'leave',self.mb.pk),self.gid,self.mb.pk,'leave')
        self.post(self.b,pk,'pay',self.wb)
        self.client.force_login(self.b)
        self.assertEqual(self.client.get(reverse('finance:group_detail',args=[self.gid])).status_code,404)
        groups.archive_group(self.a,self.token(self.a,'archive'),self.gid)
        self.post(self.a,eid,'bill',self.wa);self.post(self.a,pk,'receive',self.wa)
        self.assertEqual(wallets.balances(self.a)['wallet_total'],800000)

    def test_posting_cannot_precede_wallet_start_and_unassigned_page_is_owned(self):
        eid=self.expense()
        late=Wallet.objects.create(user=self.a,name='Ví mốc sau khoản',kind='cash',opening_balance=1000,start_date=date(2026,11,1))
        with self.assertRaises(ValidationError):self.post(self.a,eid,'bill',late)
        self.client.force_login(self.a)
        self.assertContains(self.client.get(reverse('finance:group_unassigned')),'300.000 VND')
        self.client.force_login(self.b)
        self.assertNotContains(self.client.get(reverse('finance:group_unassigned')),'300.000 VND')

    def test_settlement_receipt_replay_and_rollback_on_allocation_failure(self):
        _,share=self.debt();token=self.token(self.b,'settlement')
        pk=self.propose(share,40000,token=token)
        self.assertEqual(self.propose(share,40000,token=token),pk)
        self.assertEqual(GroupSettlement.objects.count(),1)
        with self.assertRaises(ValidationError):self.propose(share,50000,token=token)
        with patch.object(GroupAllocation,'save',side_effect=ValidationError('QA rollback')):
            with self.assertRaises(ValidationError):self.propose(share,20000)
        self.assertEqual(GroupSettlement.objects.count(),1)
        self.assertEqual(groups.obligations(self.gid)[0]['reserved'],40000)

    def test_two_direction_debts_do_not_cancel_automatically_and_cannot_leave(self):
        _,share=self.debt()
        other=groups.create_expense(self.b,self.token(self.b,'expense'),self.gid,{'amount':100000,'date':DAY,
            'description':'QA đối chiều','method':'equal','members':[self.ma.pk]})
        self.accept(other,self.a)
        states=groups.obligations(self.gid)
        self.assertEqual(sum((r['remaining'] for r in states),Decimal(0)),200000)
        with self.assertRaises(ValidationError):groups.membership_action(self.b,self.token(self.b,'leave',self.mb.pk),self.gid,self.mb.pk,'leave')

    def test_multiple_debts_fifo_and_reserved_part_not_reallocated(self):
        first,one=self.debt();second=self.expense(date=date(2026,10,11));two=self.accept(second,self.b)
        token=self.token(self.b,'settlement')
        pk=groups.propose_settlement(self.b,token,self.gid,{'amount':150000,'date':date(2026,10,12),'shares':[two.pk,one.pk]})
        self.assertEqual(dict(GroupAllocation.objects.filter(settlement_id=pk).values_list('share_id','amount')),
            {one.pk:100000,two.pk:50000})
        self.assertEqual(sum((r['available'] for r in groups.obligations(self.gid)),Decimal(0)),50000)

    def test_transaction_similar_does_not_copy_group_or_ml_evidence(self):
        from . import similar_transactions
        eid=self.expense();share=self.accept(eid,self.b)
        initial,_=similar_transactions.initial_data(share.transaction,self.b)
        self.assertNotIn('group_share',initial)
        self.assertNotIn('suggestion_id',initial)
        self.assertEqual(initial['amount'],100000)

    def test_unknown_filter_separates_group_consumption_from_unassigned_cash(self):
        eid=self.expense();self.accept(eid,self.b);self.client.force_login(self.b)
        url=reverse('finance:transaction_list')
        self.assertEqual(self.client.get(url,{'month':'2026-10','wallet':'unknown'}).context['result_count'],0)
        self.assertEqual(self.client.get(url,{'month':'2026-10','wallet':'group'}).context['result_count'],1)

    def test_cross_group_expense_participants_and_token_target_are_rejected(self):
        new=groups.create_group(self.c,groups.issue(self.c,'create'),'Nhóm QA khác')
        m=GroupMember.objects.get(group_id=new,user=self.c)
        with self.assertRaises(ValidationError):self.expense(members=[m.pk])
        eid=self.expense();share=GroupShare.objects.get(expense_id=eid,member=self.mb)
        bad=self.token(self.b,'share_accept',share.pk+100)
        with self.assertRaises(ValidationError):groups.respond_share(self.b,bad,self.gid,share.pk,True,self.cat[self.b.pk].pk)

    def test_foreign_or_forged_expense_operation_tokens(self):
        data={'amount':1,'date':DAY,'description':'QA','method':'equal','members':[self.ma.pk]}
        for token in [self.token(self.b,'expense'),self.token(self.a,'invite'),'tampered']:
            with self.assertRaises(ValidationError):groups.create_expense(self.a,token,self.gid,data)
        token=self.token(self.a,'expense')
        with patch('django.core.signing.time.time',return_value=timezone.now().timestamp()+8000):
            with self.assertRaises(ValidationError):groups.create_expense(self.a,token,self.gid,data)

    def test_expense_repeat_once_new_intent_twice_and_no_ml(self):
        data={'amount':1,'date':DAY,'description':'QA','method':'equal','members':[self.ma.pk]}
        token=self.token(self.a,'expense')
        first=groups.create_expense(self.a,token,self.gid,data)
        self.assertEqual(groups.create_expense(self.a,token,self.gid,data),first)
        self.assertNotEqual(groups.create_expense(self.a,self.token(self.a,'expense'),self.gid,data),first)
        self.assertEqual(GroupExpense.objects.count(),2);self.assertEqual(Transaction.objects.count(),0)

    def test_expense_form_supports_grouped_money_and_preview_writes_nothing(self):
        self.client.force_login(self.a)
        url=reverse('finance:group_expense_create',args=[self.gid])
        data={'operation_token':self.token(self.a,'expense'),'amount':'100.000','date':'2026-10-10',
            'description':'Mô phỏng','method':'equal','members':[self.ma.pk,self.mb.pk,self.mc.pk],'phase':'preview'}
        response=self.client.post(url,data)
        self.assertContains(response,'33.334 VND');self.assertFalse(GroupExpense.objects.exists())
        data.update(phase='confirm',confirm='on')
        self.assertEqual(self.client.post(url,data).status_code,302)
        self.assertEqual(GroupExpense.objects.count(),1)

    def test_http_ownership_csrf_no_financial_get_writes_and_html_escape(self):
        eid=self.expense();share=self.accept(eid,self.b)
        before={m.__name__:m.objects.count() for m in [Transaction,GroupExpense,GroupShare,GroupSettlement,GroupOperation,GroupWalletPosting]}
        self.client.force_login(self.a)
        for url in [reverse('finance:group_list'),reverse('finance:group_detail',args=[self.gid]),
                    reverse('finance:group_expense',args=[self.gid,eid]),reverse('finance:group_expense_create',args=[self.gid]),
                    reverse('finance:group_settlement_create',args=[self.gid])]:
            self.assertEqual(self.client.get(url).status_code,200)
        response=self.client.get(reverse('finance:group_expense',args=[self.gid,eid]))
        self.assertContains(response,'&lt;b&gt;mô phỏng&lt;/b&gt;',html=False)
        self.assertNotContains(response,'Ví B')
        self.assertEqual(before,{m.__name__:m.objects.count() for m in [Transaction,GroupExpense,GroupShare,GroupSettlement,GroupOperation,GroupWalletPosting]})
        self.assertEqual(self.client.get(reverse('finance:group_share_action',args=[self.gid,share.pk,'accept'])).status_code,404)
        outsider=get_user_model().objects.create_user('group-outside');self.client.force_login(outsider)
        self.assertEqual(self.client.get(reverse('finance:group_detail',args=[self.gid])).status_code,404)
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.a)
        self.assertEqual(csrf.post(reverse('finance:group_create'),{'name':'QA','confirm':'on'}).status_code,403)

    def test_pending_warning_and_wallet_history_labels(self):
        eid=self.expense();self.post(self.a,eid,'bill',self.wa)
        self.client.force_login(self.b)
        self.assertContains(self.client.get(reverse('finance:coverage_confirm',args=[2026,10])),'phần chi nhóm chờ')
        self.client.force_login(self.a)
        response=self.client.get(reverse('finance:wallet_detail',args=[self.wa.pk]))
        self.assertContains(response,'Dòng tiền nhóm ra')
        self.assertContains(response,reverse('finance:group_posting_detail',args=[GroupWalletPosting.objects.get().pk]))

    def test_group_list_pagination_preserves_other_sections(self):
        self.client.force_login(self.a)
        for _ in range(21):self.expense(members=[self.ma.pk])
        response=self.client.get(reverse('finance:group_detail',args=[self.gid]),{'expenses':1,'shares':2})
        self.assertContains(response,'expenses=2&amp;shares=2')
        self.assertEqual(response.context['expense_page'].paginator.count,21)

    def test_queries_no_n_plus_one_in_debts_or_wallets(self):
        eid=self.expense();self.accept(eid,self.b)
        def count(fn):
            with CaptureQueriesContext(connection) as q:fn()
            return len(q)
        debt_count=count(lambda:groups.obligations(self.gid));wallet_count=count(lambda:wallets.balances(self.a))
        for _ in range(5):
            eid=self.expense();self.accept(eid,self.b)
        self.assertEqual(count(lambda:groups.obligations(self.gid)),debt_count)
        self.assertEqual(count(lambda:wallets.balances(self.a)),wallet_count)
        self.assertLessEqual(wallet_count,5)

    def test_vietnam_day_boundary(self):
        with patch('django.utils.timezone.now',return_value=datetime(2026,10,31,17,1,tzinfo=dt_timezone.utc)):
            self.group_clock.stop();self.clock.stop()
            self.assertEqual(groups.today(),date(2026,11,1))
            groups.check_date(date(2026,11,1))
            with self.assertRaises(ValidationError):groups.check_date(date(2026,11,2))

    def test_full_debt_proposal_post_replay_redirects_same_record(self):
        _,share=self.debt();self.client.force_login(self.b)
        url=reverse('finance:group_settlement_create',args=[self.gid])
        page=self.client.get(url)
        data={'operation_token':page.context['form'].initial['operation_token'],'confirm':'on',
              'amount':'100.000','date':DAY.isoformat(),'shares':[share.pk]}
        first=self.client.post(url,data);second=self.client.post(url,data)
        self.assertEqual(first.status_code,302)
        self.assertEqual(second.status_code,302)
        self.assertEqual(first['Location'],second['Location'])
        self.assertEqual(GroupSettlement.objects.count(),1)
        self.assertEqual(groups.obligations(self.gid)[0]['reserved'],100000)

    def test_settlement_action_form_only_for_correct_party(self):
        _,share=self.debt();pk=self.propose(share)
        for user,actions in [(self.b,['confirm','reject']),(self.a,['cancel']),
                             (self.c,['confirm','reject','cancel'])]:
            self.client.force_login(user)
            for action in actions:
                url=reverse('finance:group_settlement_action',args=[self.gid,pk,action])
                self.assertEqual(self.client.get(url).status_code,404)
                self.assertEqual(self.client.post(url,{}).status_code,404)
        self.assertEqual(GroupSettlement.objects.get(pk=pk).status,'pending')

    def test_owner_management_forms_not_available_to_other_members(self):
        self.client.force_login(self.b)
        for name in ['group_archive','group_rename','group_invite']:
            url=reverse('finance:'+name,args=[self.gid])
            self.assertEqual(self.client.get(url).status_code,404)
            self.assertEqual(self.client.post(url,{}).status_code,404)

    def test_archive_requires_invitation_resolution_without_losing_history(self):
        user=get_user_model().objects.create_user('qa-archive-invite')
        mid=groups.invite(self.a,self.token(self.a,'invite'),self.gid,user.username)
        with self.assertRaises(ValidationError):groups.archive_group(self.a,self.token(self.a,'archive'),self.gid)
        self.assertEqual(GroupMember.objects.get(pk=mid).status,'invited')
        groups.membership_action(self.a,self.token(self.a,'revoke',mid),self.gid,mid,'revoke')
        groups.archive_group(self.a,self.token(self.a,'archive'),self.gid)
        self.assertEqual(GroupMember.objects.get(pk=mid).status,'revoked')

    def test_confirmation_receipt_failure_rolls_back_debt_and_reservation(self):
        _,share=self.debt();pk=self.propose(share,40000)
        before=GroupOperation.objects.count()
        with patch.object(GroupOperation,'save',side_effect=ValidationError('QA receipt failure')):
            with self.assertRaises(ValidationError):self.confirm(pk)
        self.assertEqual(GroupOperation.objects.count(),before)
        self.assertEqual(GroupSettlement.objects.get(pk=pk).status,'pending')
        state=groups.obligations(self.gid)[0]
        self.assertEqual((state['remaining'],state['reserved'],state['available']),(100000,40000,60000))
        self.assertFalse(GroupWalletPosting.objects.exists())

    def test_shared_pages_and_forms_never_expose_other_private_wallet_or_category(self):
        secret_category=Category.objects.create(user=self.b,name='PRIVATE-B-CATEGORY-QA',kind='expense')
        eid=self.expense();share=GroupShare.objects.get(expense_id=eid,member=self.mb)
        groups.respond_share(self.b,self.token(self.b,'share_accept',share.pk),self.gid,share.pk,True,secret_category.pk)
        self.client.force_login(self.a)
        own=GroupShare.objects.get(expense_id=eid,member=self.ma)
        for name,args in [('group_detail',[self.gid]),('group_expense',[self.gid,eid]),
                ('group_share_action',[self.gid,own.pk,'accept']),('group_posting',[self.gid,eid,'bill'])]:
            response=self.client.get(reverse('finance:'+name,args=args))
            self.assertEqual(response.status_code,200)
            self.assertNotContains(response,secret_category.name)
            self.assertNotContains(response,self.wb.name)
        pk=self.propose(share,40000);self.confirm(pk)
        posting=self.post(self.b,pk,'pay',self.wb)
        self.assertEqual(self.client.get(reverse('finance:group_posting_detail',args=[posting])).status_code,404)


@skipUnless(connection.vendor=='postgresql','Real row-lock evidence requires PostgreSQL QA')
class GroupConcurrencyTests(GroupFixture,TransactionTestCase):
    def race(self,functions):
        barrier=Barrier(len(functions));results=Queue()
        def worker(fn):
            close_old_connections()
            try:
                barrier.wait(timeout=10);results.put(('ok',fn()))
            except ValidationError:results.put(('conflict',None))
            except Exception as exc:results.put(('error',type(exc).__name__))
            finally:close_old_connections()
        threads=[Thread(target=worker,args=(fn,)) for fn in functions]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=30);self.assertFalse(thread.is_alive())
        rows=[results.get_nowait() for _ in threads]
        self.assertNotIn('error',[r[0] for r in rows],rows)
        return rows

    def test_two_pending_requests_cannot_reserve_more_than_debt(self):
        _,share=self.debt();tokens=[self.token(self.b,'settlement') for _ in range(2)]
        rows=self.race([lambda t=t:self.propose(share,60000,token=t) for t in tokens])
        self.assertEqual(sorted(r[0] for r in rows),['conflict','ok'])
        state=groups.obligations(self.gid)[0];self.assertEqual((state['reserved'],state['available']),(60000,40000))

    def test_same_confirm_twice_and_independent_pending_both_commit(self):
        _,share=self.debt();pk=self.propose(share,40000)
        token=self.token(self.a,'settlement_confirm',pk)
        self.race([lambda:groups.settlement_action(self.a,token,self.gid,pk,'confirm') for _ in range(2)])
        self.assertEqual(groups.obligations(self.gid)[0]['remaining'],60000)
        other=self.propose(share,30000);last=self.propose(share,30000)
        self.race([lambda p=p:self.confirm(p) for p in [other,last]])
        self.assertEqual(groups.obligations(self.gid)[0]['remaining'],0)

    def test_accept_share_and_post_wallet_have_one_source_under_race(self):
        eid=self.expense();share=GroupShare.objects.get(expense_id=eid,member=self.mb)
        token=self.token(self.b,'share_accept',share.pk)
        self.race([lambda:groups.respond_share(self.b,token,self.gid,share.pk,True,self.cat[self.b.pk].pk) for _ in range(2)])
        self.assertEqual(Transaction.objects.count(),1)
        self.race([lambda:self.post(self.a,eid,'bill',self.wa) for _ in range(2)])
        self.assertEqual(GroupWalletPosting.objects.count(),1)
        self.assertEqual(wallets.balances(self.a)['wallet_total'],700000)

    def test_revoke_racing_join_has_no_active_revoked_member(self):
        u=get_user_model().objects.create_user('race-invite')
        mid=groups.invite(self.a,self.token(self.a,'invite'),self.gid,u.username)
        jt=self.token(u,'join',mid);rt=self.token(self.a,'revoke',mid)
        rows=self.race([lambda:groups.membership_action(u,jt,self.gid,mid,'join'),
                        lambda:groups.membership_action(self.a,rt,self.gid,mid,'revoke')])
        self.assertEqual(sorted(r[0] for r in rows),['conflict','ok'])
        self.assertIn(GroupMember.objects.get(pk=mid).status,['active','revoked'])


@skipUnless(connection.vendor=='sqlite','File-lock evidence specifically for SQLite QA')
class GroupSQLiteConcurrencyTests(GroupFixture,TransactionTestCase):
    def setUp(self):
        if 'memory' in str(connection.settings_dict['NAME']):
            self.skipTest('Use a file-backed SQLite TEST database for independent connections')
        super().setUp()

    def race(self,functions):
        barrier=Barrier(len(functions));results=Queue()
        def worker(fn):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                results.put(('ok',fn()))
            except ValidationError:
                results.put(('conflict',None))
            except OperationalError as exc:
                # A bounded SQLite busy response is permitted, never a partial
                # financial result. Do not accept unrelated database failures.
                results.put(('busy' if any(word in str(exc).lower() for word in ['locked','busy']) else 'error',None))
            except Exception as exc:
                results.put(('error',type(exc).__name__))
            finally:
                close_old_connections()
        threads=[Thread(target=worker,args=(fn,)) for fn in functions]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=30);self.assertFalse(thread.is_alive())
        rows=[results.get_nowait() for _ in threads]
        self.assertNotIn('error',[row[0] for row in rows],rows)
        self.assertIn('ok',[row[0] for row in rows],rows)
        return rows

    def test_competing_reservations_never_overbook_file_database(self):
        _,share=self.debt();tokens=[self.token(self.b,'settlement') for _ in range(2)]
        self.race([lambda t=t:self.propose(share,60000,token=t) for t in tokens])
        self.assertEqual(GroupSettlement.objects.count(),1)
        state=groups.obligations(self.gid)[0]
        self.assertEqual((state['remaining'],state['reserved'],state['available']),(100000,60000,40000))

    def test_duplicate_confirmation_changes_debt_once_file_database(self):
        _,share=self.debt();pk=self.propose(share,40000)
        token=self.token(self.a,'settlement_confirm',pk)
        self.race([lambda:groups.settlement_action(self.a,token,self.gid,pk,'confirm') for _ in range(2)])
        self.assertEqual(groups.obligations(self.gid)[0]['remaining'],60000)
        self.assertEqual(GroupSettlement.objects.filter(status='confirmed').count(),1)

    def test_two_wallet_claims_for_same_source_have_one_effect_file_database(self):
        eid=self.expense()
        self.race([lambda:self.post(self.a,eid,'bill',self.wa) for _ in range(2)])
        self.assertEqual(GroupWalletPosting.objects.count(),1)
        self.assertEqual(wallets.balances(self.a)['wallet_total'],700000)
        self.assertEqual(Transaction.objects.count(),0)
