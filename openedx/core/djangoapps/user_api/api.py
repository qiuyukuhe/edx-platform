from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.utils.translation import ugettext as _

from openedx.core.djangoapps.user_api.accounts import (
    EMAIL_MIN_LENGTH,
    EMAIL_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    PASSWORD_MAX_LENGTH
)
from openedx.core.djangoapps.user_api.helpers import FormDescription
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

from student.forms import get_registration_extension_form


def get_password_reset_response():
    form_desc = FormDescription("post", reverse("password_change_request"))

    # Translators: This label appears above a field on the password reset
    # form meant to hold the user's email address.
    email_label = _(u"Email")

    # Translators: This example email address is used as a placeholder in
    # a field on the password reset form meant to hold the user's email address.
    email_placeholder = _(u"username@domain.com")

    # Translators: These instructions appear on the password reset form,
    # immediately below a field meant to hold the user's email address.
    email_instructions = _(u"The email address you used to register with {platform_name}").format(
        platform_name=configuration_helpers.get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
    )

    form_desc.add_field(
        "email",
        field_type="email",
        label=email_label,
        placeholder=email_placeholder,
        instructions=email_instructions,
        restrictions={
            "min_length": EMAIL_MIN_LENGTH,
            "max_length": EMAIL_MAX_LENGTH,
        }
    )

    return HttpResponse(form_desc.to_json(), content_type="application/json")


def get_login_session_response():
    form_desc = FormDescription("post", reverse("user_api_login_session"))

    # Translators: This label appears above a field on the login form
    # meant to hold the user's email address.
    email_label = _(u"Email")

    # Translators: This example email address is used as a placeholder in
    # a field on the login form meant to hold the user's email address.
    email_placeholder = _(u"username@domain.com")

    # Translators: These instructions appear on the login form, immediately
    # below a field meant to hold the user's email address.
    email_instructions = _("The email address you used to register with {platform_name}").format(
        platform_name=configuration_helpers.get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
    )

    form_desc.add_field(
        "email",
        field_type="email",
        label=email_label,
        placeholder=email_placeholder,
        instructions=email_instructions,
        restrictions={
            "min_length": EMAIL_MIN_LENGTH,
            "max_length": EMAIL_MAX_LENGTH,
        }
    )

    # Translators: This label appears above a field on the login form
    # meant to hold the user's password.
    password_label = _(u"Password")

    form_desc.add_field(
        "password",
        label=password_label,
        field_type="password",
        restrictions={
            "min_length": PASSWORD_MIN_LENGTH,
            "max_length": PASSWORD_MAX_LENGTH,
        }
    )

    form_desc.add_field(
        "remember",
        field_type="checkbox",
        label=_("Remember me"),
        default=False,
        required=False,
    )

    return HttpResponse(form_desc.to_json(), content_type="application/json")


def get_registration_response(self, request):
    form_desc = FormDescription("post", reverse("user_api_registration"))
    self._apply_third_party_auth_overrides(request, form_desc)

    # Custom form fields can be added via the form set in settings.REGISTRATION_EXTENSION_FORM
    custom_form = get_registration_extension_form()

    if custom_form:
        # Default fields are always required
        for field_name in self.DEFAULT_FIELDS:
            self.field_handlers[field_name](form_desc, required=True)

        for field_name, field in custom_form.fields.items():
            restrictions = {}
            if getattr(field, 'max_length', None):
                restrictions['max_length'] = field.max_length
            if getattr(field, 'min_length', None):
                restrictions['min_length'] = field.min_length
            field_options = getattr(
                getattr(custom_form, 'Meta', None), 'serialization_options', {}
            ).get(field_name, {})
            field_type = field_options.get('field_type', FormDescription.FIELD_TYPE_MAP.get(field.__class__))
            if not field_type:
                raise ImproperlyConfigured(
                    "Field type '{}' not recognized for registration extension field '{}'.".format(
                        field_type,
                        field_name
                    )
                )
            form_desc.add_field(
                field_name, label=field.label,
                default=field_options.get('default'),
                field_type=field_options.get('field_type', FormDescription.FIELD_TYPE_MAP.get(field.__class__)),
                placeholder=field.initial, instructions=field.help_text, required=field.required,
                restrictions=restrictions,
                options=getattr(field, 'choices', None), error_messages=field.error_messages,
                include_default_option=field_options.get('include_default_option'),
            )

        # Extra fields configured in Django settings
        # may be required, optional, or hidden
        for field_name in self.EXTRA_FIELDS:
            if self._is_field_visible(field_name):
                self.field_handlers[field_name](
                    form_desc,
                    required=self._is_field_required(field_name)
                )
    else:
        # Go through the fields in the fields order and add them if they are required or visible
        for field_name in self.field_order:
            if field_name in self.DEFAULT_FIELDS:
                self.field_handlers[field_name](form_desc, required=True)
            elif self._is_field_visible(field_name):
                self.field_handlers[field_name](
                    form_desc,
                    required=self._is_field_required(field_name)
                )

    return HttpResponse(form_desc.to_json(), content_type="application/json")
