from django import forms

class AudioUploadForm(forms.Form):
    audio_file = forms.FileField()
