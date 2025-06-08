from django import forms
from django.contrib.auth.models import User
from .models import Message

class MessageForm(forms.ModelForm):
    destinataire = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Destinataire"
    )
    
    class Meta:
        model = Message
        fields = ['destinataire', 'objet', 'contenu']
        widgets = {
            'objet': forms.TextInput(attrs={'class': 'form-control'}),
            'contenu': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclure l'utilisateur actuel de la liste des destinataires possibles
        if hasattr(self, 'request') and self.request.user.is_authenticated:
            self.fields['destinataire'].queryset = User.objects.exclude(
                id=self.request.user.id
            )
