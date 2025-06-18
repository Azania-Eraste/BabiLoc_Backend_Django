from django import forms
from .models import Bien, User  # ou Estate ou ce que tu as

class BienForm(forms.ModelForm):
    class Meta:
        model = Bien
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(BienForm, self).__init__(*args, **kwargs)
        self.fields['owner'].queryset = User.objects.filter(is_vendor=True)
