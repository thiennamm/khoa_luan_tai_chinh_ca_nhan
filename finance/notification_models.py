from django.conf import settings
from django.db import models
from django.db.models import Q


class GroupNotification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    invitation = models.ForeignKey('finance.GroupMember', null=True, on_delete=models.CASCADE)
    invitation_version = models.PositiveIntegerField(null=True)
    share = models.OneToOneField('finance.GroupShare', null=True, on_delete=models.CASCADE)
    settlement = models.OneToOneField('finance.GroupSettlement', null=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ['-created_at', '-pk']
        indexes = [
            models.Index(fields=['recipient', '-created_at', '-id'], name='group_notice_inbox_idx'),
            models.Index(fields=['recipient', 'read_at'], name='group_notice_unread_idx'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['invitation', 'invitation_version'], name='group_notice_invite_once'),
            models.CheckConstraint(
                condition=(
                    Q(invitation__isnull=False, invitation_version__isnull=False, invitation_version__gte=1,
                      share__isnull=True, settlement__isnull=True)
                    | Q(invitation__isnull=True, invitation_version__isnull=True,
                        share__isnull=False, settlement__isnull=True)
                    | Q(invitation__isnull=True, invitation_version__isnull=True,
                        share__isnull=True, settlement__isnull=False)
                ),
                name='group_notice_one_target',
            ),
        ]

    @property
    def title(self):
        if self.invitation_id:
            return 'Bạn được mời vào nhóm'
        if self.share_id:
            return 'Có phần chia cần xác nhận'
        return 'Có đề nghị hoàn trả cần xác nhận'
