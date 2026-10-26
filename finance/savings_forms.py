from django import forms
from .models import SavingsGoal, SavingsEntry
from .money_fields import amount_field
from .savings_calendar import today


class OperationForm(forms.Form):
    operation_token = forms.CharField(widget=forms.HiddenInput, max_length=2000)


class SavingsGoalForm(forms.ModelForm):
    operation_token = forms.CharField(widget=forms.HiddenInput, max_length=2000)
    amount = amount_field(SavingsGoal)

    class Meta:
        model = SavingsGoal
        fields = ['name','amount','start_date','due_date','note']
        widgets = {key: forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'}) for key in ['start_date','due_date']}
        widgets['note'] = forms.Textarea(attrs={'rows':2})

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = user


class SavingsEntryForm(forms.ModelForm):
    operation_token = forms.CharField(widget=forms.HiddenInput, max_length=2000)
    amount = amount_field(SavingsEntry)

    class Meta:
        model = SavingsEntry
        fields = ['kind','amount','date','note']
        widgets = {'date': forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'}),
            'note': forms.Textarea(attrs={'rows':2})}

    def __init__(self, *args, goal, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.goal = goal
        self.fields['date'].widget.attrs['max'] = today().isoformat()
        self.fields['date'].widget.attrs['min'] = goal.start_date.isoformat()
        if self.instance.pk:
            self.fields['confirm'] = forms.BooleanField(label='Tôi xác nhận sửa bản ghi phân bổ này.')
