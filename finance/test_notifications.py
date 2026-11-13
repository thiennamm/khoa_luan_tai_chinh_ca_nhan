from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from . import groups
from .models import GroupExpense, GroupMember, GroupNotification, GroupSettlement, GroupShare, Transaction
from .test_groups import GroupFixture


class NotificationTests(GroupFixture, TestCase):
    def setUp(self):
        super().setUp()
        GroupNotification.objects.all().delete()
        self.client.force_login(self.b)

    def inbox(self):
        return self.client.get(reverse('finance:notification_inbox'))

    def open_url(self, notice):
        return reverse('finance:notification_open', args=[notice.pk])

    def assert_unread(self, response, count):
        self.assertContains(response, f'Thông báo: {count} chưa đọc')

    def new_invitation(self):
        gid = groups.create_group(self.a, self.token(self.a, 'create', gid=0), 'Nhóm thông báo')
        token = self.token(self.a, 'invite', gid=gid)
        member = groups.invite(self.a, token, gid, self.b.username)
        self.assertEqual(groups.invite(self.a, token, gid, self.b.username), member)
        return gid, member, GroupNotification.objects.get(invitation_id=member)

    def test_invitation_open_does_not_join_and_processed_invitation_opens_group(self):
        self.assertContains(self.inbox(), 'Bạn chưa có thông báo')
        gid, member, notice = self.new_invitation()
        self.assert_unread(self.inbox(), 1)
        self.assertContains(self.inbox(), 'Bạn được mời vào nhóm')
        response = self.client.post(self.open_url(notice), follow=True)
        self.assertContains(response, 'Chấp nhận lời mời')
        self.assertContains(response, 'Từ chối lời mời')
        self.assert_unread(response, 0)
        self.assertEqual(GroupMember.objects.get(pk=member).status, 'invited')
        notice.refresh_from_db()
        opened = notice.read_at
        self.assertIsNotNone(opened)
        groups.membership_action(self.b, self.token(self.b, 'join', member, gid), gid, member, 'join')
        response = self.client.post(self.open_url(notice), follow=True)
        self.assertContains(response, 'Lời mời này đã được chấp nhận.')
        self.assertEqual(response.request['PATH_INFO'], reverse('finance:group_detail', args=[gid]))
        notice.refresh_from_db()
        self.assertEqual(notice.read_at, opened)

    def test_old_invitation_cannot_open_reissued_invitation(self):
        gid, member, notice = self.new_invitation()
        old_link = self.client.post(self.open_url(notice))['Location']
        groups.membership_action(self.a, self.token(self.a, 'revoke', member, gid), gid, member, 'revoke')
        self.assertContains(self.client.get(old_link, follow=True), 'Đã thu hồi')
        groups.invite(self.a, self.token(self.a, 'invite', gid=gid), gid, self.b.username)
        response = self.client.post(self.open_url(notice), follow=True)
        self.assertContains(response, 'Đã được thay thế')
        self.assertEqual(response.request['PATH_INFO'], reverse('finance:group_list'))
        self.assertContains(self.client.get(old_link, follow=True), 'Đã được thay thế')
        new_notice = GroupNotification.objects.get(invitation_id=member, invitation_version=2)
        self.assertIsNone(new_notice.read_at)
        self.assertContains(self.client.post(self.open_url(new_notice), follow=True), 'Chấp nhận lời mời')

    def test_share_and_repayment_open_without_confirming(self):
        eid = self.expense(members=[self.mb.pk])
        share = GroupShare.objects.get(expense_id=eid)
        share_notice = GroupNotification.objects.get(share=share, recipient=self.b)
        self.assert_unread(self.inbox(), 1)
        response = self.client.post(self.open_url(share_notice), follow=True)
        self.assertEqual(response.request['PATH_INFO'], reverse('finance:group_expense', args=[self.gid, eid]))
        self.assertContains(response, 'Chờ xác nhận')
        self.assert_unread(response, 0)
        share.refresh_from_db()
        self.assertEqual(share.status, 'pending')
        self.assertFalse(Transaction.objects.exists())
        share = self.accept(eid, self.b)
        self.assertContains(self.client.post(self.open_url(share_notice), follow=True), 'Đã chấp nhận')

        settlement = self.propose(share)
        notice = GroupNotification.objects.get(settlement_id=settlement, recipient=self.a)
        self.assertNotContains(self.inbox(), 'Có đề nghị hoàn trả cần xác nhận')
        self.client.force_login(self.a)
        self.assert_unread(self.inbox(), 1)
        response = self.client.post(self.open_url(notice), follow=True)
        self.assertEqual(response.request['PATH_INFO'], reverse('finance:group_settlement', args=[self.gid, settlement]))
        self.assertContains(response, 'Chờ xác nhận')
        self.assert_unread(response, 0)
        self.assertEqual(GroupSettlement.objects.get(pk=settlement).status, 'pending')
        self.assertEqual(Transaction.objects.count(), 1)
        with patch('finance.group_views.timezone.now', return_value=timezone.now()+timedelta(days=8)):
            self.assertContains(self.client.post(self.open_url(notice), follow=True), 'Đã hết hạn')
        self.confirm(settlement)
        self.assertContains(self.client.post(self.open_url(notice), follow=True), 'Đã xác nhận')

    def test_open_requires_recipient_post_and_csrf(self):
        _, _, notice = self.new_invitation()
        self.assertEqual(self.client.get(self.open_url(notice)).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.b)
        self.assertEqual(strict.post(self.open_url(notice)).status_code, 403)
        self.client.force_login(self.a)
        self.assertContains(self.inbox(), 'Bạn chưa có thông báo')
        self.assertEqual(self.client.post(self.open_url(notice)).status_code, 404)
        notice.refresh_from_db()
        self.assertIsNone(notice.read_at)
        self.client.logout()
        self.assertEqual(self.inbox().status_code, 302)

    def test_voided_expense_is_shown_and_former_member_goes_to_group_list(self):
        eid = self.expense(members=[self.mb.pk])
        notice = GroupNotification.objects.get(share__expense_id=eid)
        groups.void_expense(self.a, self.token(self.a, 'void', eid), self.gid, eid)
        response = self.client.post(self.open_url(notice), follow=True)
        self.assertContains(response, 'Đã hủy')
        groups.membership_action(self.b, self.token(self.b, 'leave', self.mb.pk), self.gid, self.mb.pk, 'leave')
        response = self.client.post(self.open_url(notice), follow=True)
        self.assertContains(response, 'Nội dung thông báo không còn truy cập được.')
        self.assertEqual(response.request['PATH_INFO'], reverse('finance:group_list'))

    def test_notice_and_expense_are_atomic_and_replayed_operation_does_not_duplicate(self):
        data = {'amount': 300000, 'date': groups.today(), 'description': 'QA', 'method': 'equal',
                'members': [self.ma.pk, self.mb.pk]}
        token = self.token(self.a, 'expense')
        with patch('finance.groups.GroupNotification.objects.bulk_create', side_effect=IntegrityError('QA rollback')):
            with self.assertRaises(IntegrityError):
                groups.create_expense(self.a, token, self.gid, data)
        self.assertFalse(GroupExpense.objects.exists())
        self.assertFalse(GroupNotification.objects.exists())
        expense = groups.create_expense(self.a, token, self.gid, data)
        self.assertEqual(groups.create_expense(self.a, token, self.gid, data), expense)
        self.assertEqual(GroupNotification.objects.count(), 2)

    def test_newest_first_and_pagination_do_not_mark_read(self):
        first = self.expense(members=[self.mb.pk])
        for _ in range(20):
            self.expense(members=[self.mb.pk])
        first_notice = GroupNotification.objects.get(share__expense_id=first)
        newest = GroupNotification.objects.filter(recipient=self.b).first()
        response = self.inbox()
        self.assert_unread(response, 21)
        self.assertContains(response, self.open_url(newest))
        self.assertNotContains(response, self.open_url(first_notice))
        self.assertContains(self.client.get(reverse('finance:notification_inbox'), {'page': 2}), self.open_url(first_notice))
        self.assertFalse(GroupNotification.objects.filter(read_at__isnull=False).exists())
