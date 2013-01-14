from django import http
from django.conf import settings
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_POST

import commonware.log
from django_browserid import get_audience, verify as verify_assertion
from django_browserid.forms import BrowserIDForm
from session_csrf import anonymous_csrf_exempt

from webpay.base.decorators import json_view
from utils import set_user

log = commonware.log.getLogger('w.auth')


@anonymous_csrf_exempt
@require_POST
@json_view
def verify(request):
    form = BrowserIDForm(data=request.POST)
    if form.is_valid():
        url = settings.BROWSERID_VERIFICATION_URL
        audience = get_audience(request)
        extra_params = {'forceIssuer': settings.BROWSERID_UNVERIFIED_ISSUER,
                        'allowUnverified': 'true'}
        assertion = form.cleaned_data['assertion']

        log.info('verifying Persona assertion. url: %s, audience: %s, '
                 'extra_params: %s, assertion: %s' % (url, audience,
                                                      extra_params, assertion))
        result = verify_assertion(assertion, audience, extra_params)
        if result:
            log.info('Persona assertion ok: %s' % result)
            email = result.get('unverified-email', result.get('email'))
            set_user(request, email)
            return {'has_pin': request.session.get('uuid_has_pin'),
                    'pin_create': reverse('pin.create')}

        log.error('Persona assertion failed.')

    request.session.clear()
    return http.HttpResponseBadRequest()


def logout(request):
    # TODO(Wraithan): implement logout view
    return
