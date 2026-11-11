from decimal import Decimal
from django import forms
from .money_fields import amount_field, VNDAmountField, VNDInput
from .group_models import GroupExpense, GroupSettlement, GroupMember
from .models import Category, Wallet
from . import groups


class OperationForm(forms.Form):
    operation_token = forms.CharField(max_length=2000,widget=forms.HiddenInput)
    confirm = forms.BooleanField(label='Tôi đã kiểm tra và xác nhận thao tác này.')


class GroupForm(OperationForm):
    name = forms.CharField(label='Tên nhóm',max_length=80)


class InvitationForm(OperationForm):
    username = forms.CharField(label='Tên đăng nhập chính xác',max_length=150,
        help_text='Người được mời phải tự chấp nhận. Không chia sẻ ví hoặc danh mục riêng.')


class ExpenseForm(OperationForm):
    amount = amount_field(GroupExpense)
    amount.label = 'Tổng tiền đã trả'
    date = forms.DateField(label='Ngày đã trả thực tế',widget=forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'}))
    description = forms.CharField(label='Mô tả chia sẻ với nhóm',max_length=300,widget=forms.Textarea(attrs={'rows':2}))
    method = forms.ChoiceField(label='Cách chia',choices=[('equal','Chia đều'),('exact','Nhập phần tiền')])
    members = forms.TypedMultipleChoiceField(label='Người chịu chi',coerce=int,widget=forms.CheckboxSelectMultiple)
    confirm = forms.BooleanField(required=False,label='Tôi xác nhận đã trả toàn bộ tiền, đã kiểm phần chia và giới hạn sửa sai.')

    def __init__(self,*args,group,user,**kwargs):
        super().__init__(*args,**kwargs)
        self.members = list(GroupMember.objects.filter(group=group,status='active').select_related('user').order_by('pk'))
        self.fields['members'].choices = [(m.pk,m.user.get_username()) for m in self.members]
        self.fields['date'].widget.attrs['max'] = groups.today().isoformat()
        for member in self.members:
            self.fields[f'part_{member.pk}'] = VNDAmountField(label=f'Phần tiền của {member.user.get_username()} (khi chia cụ thể)',
                required=False,max_digits=15,decimal_places=0,min_value=Decimal(0),
                widget=VNDInput(attrs={'inputmode':'numeric','data-vnd-input':'true'}))

    def clean(self):
        data = super().clean()
        if self.errors:
            return data
        groups.check_date(data['date'])
        exact = {pk:data.get(f'part_{pk}') for pk in data['members']}
        data['parts'] = groups.split(data['amount'],data['members'],data['method'],exact)
        data['exact'] = exact if data['method']=='exact' else None
        return data

    def payload(self):
        return {key:self.cleaned_data[key] for key in ['amount','date','description','method','members','exact']}


class ShareForm(OperationForm):
    category = forms.ModelChoiceField(label='Danh mục chi của riêng bạn',queryset=Category.objects.none())

    def __init__(self,*args,user,share,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['category'].queryset = Category.objects.filter(user=user,kind='expense')
        self.fields['category'].required = share.amount > 0


class SettlementForm(OperationForm):
    amount = amount_field(GroupSettlement)
    amount.label = 'Số tiền đã hoàn trả'
    date = forms.DateField(label='Ngày hoàn trả thực tế',widget=forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'}))
    shares = forms.TypedMultipleChoiceField(label='Các phần nợ muốn hoàn cho cùng một người',coerce=int,
        widget=forms.CheckboxSelectMultiple)

    def __init__(self,*args,rows,**kwargs):
        from .money import format_vnd
        super().__init__(*args,**kwargs)
        self.fields['date'].widget.attrs['max'] = groups.today().isoformat()
        self.fields['shares'].choices = [(row['share'].pk,
            f"{row['share'].expense.payer.user.get_username()} · {row['share'].expense.description} · Còn có thể đề nghị {format_vnd(row['available'])}") for row in rows]


class PostingForm(OperationForm):
    wallet = forms.ModelChoiceField(label='Ví của riêng bạn',queryset=Wallet.objects.none())

    def __init__(self,*args,user,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['wallet'].queryset = Wallet.objects.filter(user=user,archived=False)
