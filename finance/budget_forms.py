from django import forms
from .models import Budget, Category
from .money_fields import amount_field


class BudgetForm(forms.ModelForm):
    amount = amount_field(Budget)
    month = forms.DateField(label='Tháng', input_formats=['%Y-%m'],
        widget=forms.DateInput(format='%Y-%m', attrs={'type': 'month'}),
        error_messages={'invalid': 'Tháng không hợp lệ. Vui lòng chọn lại.'})

    class Meta:
        model = Budget
        fields = ['month', 'category', 'amount']

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = user
        self.fields['category'].queryset = Category.objects.filter(user=user, kind='expense')
        self.fields['category'].empty_label = 'Ngân sách tổng (mọi khoản chi)'
        self.fields['category'].error_messages['invalid_choice'] = 'Chỉ chọn danh mục chi của chính bạn.'

    def clean(self):
        cleaned = super().clean()
        month = cleaned.get('month')
        if month and month.year == 9999 and month.month == 12:
            self.add_error('month', 'Vui lòng chọn tháng trước tháng 12/9999.')
        if month and 'category' in cleaned:
            duplicates = Budget.objects.filter(user=self.instance.user, month=month,
                category=cleaned['category']).exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise forms.ValidationError('Đã có ngân sách cùng tháng và phạm vi. Hãy sửa ngân sách hiện có.')
        return cleaned
