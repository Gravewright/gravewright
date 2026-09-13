import base64
import binascii
from urllib.parse import urlsplit

from django import forms
from django.db.models.fields.files import FieldFile
from django.core.files.uploadedfile import SimpleUploadedFile

from .catalog import list_rulesets
from .models import Campaign

MAX_COVER_BYTES = 5_000_000
ALLOWED_IMAGES = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp'}


class CampaignForm(forms.ModelForm):
    name = forms.CharField(min_length=2, max_length=80)
    description = forms.CharField(max_length=500, required=False)
    system = forms.ChoiceField(required=False)
    image = forms.CharField(required=False, max_length=7_000_000)
    cover = forms.ImageField(required=False)

    class Meta:
        model = Campaign
        fields = ['name', 'description', 'system', 'cover']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [(row['systemId'], row['title']) for row in list_rulesets()]
        current = self.instance.system
        if not self.instance._state.adding and current and current not in dict(choices):
            # A removed/revoked system must not prevent an existing campaign edit.
            choices.append((current, f'{current} (unavailable)'))
        self.fields['system'].choices = [('', '')] + choices

    def clean_name(self):
        return ' '.join(self.cleaned_data['name'].split())

    def clean_cover(self):
        upload = self.cleaned_data.get('cover')
        if isinstance(upload, FieldFile):
            return upload
        if upload and (upload.size > MAX_COVER_BYTES or upload.image.format not in ('PNG', 'JPEG', 'WEBP')):
            raise forms.ValidationError('invalid_container_image')
        return upload

    def clean_image(self):
        image = self.cleaned_data['image']
        if not image:
            return ''
        if image.startswith('data:'):
            try:
                header, payload = image.split(',', 1)
                mime = header.removeprefix('data:').removesuffix(';base64')
                if mime not in ALLOWED_IMAGES or not header.endswith(';base64'):
                    raise ValueError
                raw = base64.b64decode(payload, validate=True)
                if len(raw) > MAX_COVER_BYTES:
                    raise ValueError
                upload = forms.ImageField().clean(SimpleUploadedFile(
                    f'cover.{ALLOWED_IMAGES[mime]}', raw, content_type=mime))
                if upload.image.format not in ('PNG', 'JPEG', 'WEBP'):
                    raise ValueError
                self.cleaned_data['cover'] = upload
                return ''
            except (ValueError, binascii.Error, forms.ValidationError):
                raise forms.ValidationError('invalid_container_image') from None
        # Allow retaining only this campaign's own protected cover URL.
        if self.instance.pk and self.instance.cover and image == f'/campaigns/{self.instance.pk}/cover':
            return image
        try:
            parts = urlsplit(image)
            if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
                raise ValueError
            forms.URLField(max_length=2048).clean(image)
        except (ValueError, forms.ValidationError):
            raise forms.ValidationError('invalid_container_image') from None
        return image
