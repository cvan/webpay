from django.core.urlresolvers import reverse

from mock import ANY, patch
from nose.tools import eq_

from lib.solitude.api import client
from lib.solitude.errors import ERROR_STRINGS
from webpay.auth.tests import SessionTestCase
from webpay.pay import get_payment_url


class PinViewTestCase(SessionTestCase):
    url_name = ''

    def setUp(self):
        self.url = reverse(self.url_name)
        self.verify('a:b')


class CreatePinViewTest(PinViewTestCase):
    url_name = 'pin.create'

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch('lib.solitude.api.client.change_pin', auto_spec=True)
    @patch('webpay.pin.views.set_user_has_pin', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {})
    def test_buyer_does_not_exist(self, set_user_has_pin, change_pin,
                                  create_buyer):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert create_buyer.called
        assert not change_pin.called
        set_user_has_pin.assert_called_with(ANY, True)
        assert res['Location'].endswith(reverse('pin.confirm'))

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch('lib.solitude.api.client.change_pin', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': 'some:uuid'})
    def test_buyer_does_exist_with_no_pin(self, change_pin, create_buyer):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not create_buyer.called
        assert change_pin.called
        assert res['Location'].endswith(reverse('pin.confirm'))

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch('lib.solitude.api.client.change_pin', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': 'some:uuid',
                                                  'pin': 'fake'})
    def test_buyer_does_exist_with_pin(self, change_pin, create_buyer):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not create_buyer.called
        assert not change_pin.called
        self.assertTemplateUsed(res, 'pin/create.html')

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': 'some:uuid'})
    @patch.object(client, 'change_pin',
                  lambda x, y: {'errors':
                                {'pin':
                                 ['PIN must be exactly 4 numbers long']}})
    def test_buyer_does_exist_with_short_pin(self, create_buyer):
        res = self.client.post(self.url, data={'pin': '123'})
        assert not create_buyer.called
        form = res.context['form']
        eq_(form.errors.get('pin'),
            [ERROR_STRINGS['PIN must be exactly 4 numbers long']])

    @patch('lib.solitude.api.client.create_buyer', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': 'some:uuid'})
    @patch.object(client, 'change_pin',
                  lambda x, y: {'errors':
                                {'pin': ['PIN may only consists of numbers']}})
    def test_buyer_does_exist_with_alpha_pin(self, create_buyer):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert not create_buyer.called
        form = res.context['form']
        eq_(form.errors.get('pin'),
            [ERROR_STRINGS['PIN may only consists of numbers']])


class VerifyPinViewTest(PinViewTestCase):
    url_name = 'pin.verify'

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch.object(client, 'verify_pin', lambda x, y: {'locked': False,
                                                      'valid': True})
    def test_good_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert res['Location'].endswith(get_payment_url())

    @patch.object(client, 'verify_pin', lambda x, y: {'locked': False,
                                                      'valid': False})
    def test_bad_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        self.assertTemplateUsed(res, 'pin/verify.html')

    @patch.object(client, 'verify_pin', lambda x, y: {'locked': True,
                                                      'valid': False})
    def test_locked_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        self.assertTemplateUsed(res, 'pin/verify.html')

    @patch.object(client, 'verify_pin')
    def test_uuid_used(self, verify_pin):
        verify_pin.return_value = {'locked': False, 'valid': True}
        self.client.post(self.url, data={'pin': '1234'})
        eq_(verify_pin.call_args[0][0], 'a:b')


class ConfirmPinViewTest(PinViewTestCase):
    url_name = 'pin.confirm'

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch.object(client, 'confirm_pin', lambda x, y: True)
    def test_good_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert res['Location'].endswith(get_payment_url())

    @patch.object(client, 'confirm_pin', lambda x, y: False)
    def test_bad_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        self.assertTemplateUsed(res, 'pin/confirm.html')

    @patch.object(client, 'confirm_pin')
    def test_uuid_used(self, confirm_pin):
        confirm_pin.return_value = True
        self.client.post(self.url, data={'pin': '1234'})
        eq_(confirm_pin.call_args[0][0], 'a:b')


class ResetStartViewTest(PinViewTestCase):
    url_name = 'pin.reset_start'

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch('lib.solitude.api.client.set_needs_pin_reset', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    def test_view(self, set_needs_pin_reset):
        res = self.client.get(self.url)
        assert set_needs_pin_reset.called
        assert res['Location'].endswith(reverse('auth.logout'))


class ResetNewPinViewTest(PinViewTestCase):
    url_name = 'pin.reset_new_pin'

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch('lib.solitude.api.client.set_new_pin', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    def test_valid_form(self, set_new_pin):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert set_new_pin.called
        assert res['Location'].endswith(reverse('pin.reset_confirm'))

    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    @patch.object(client, 'set_new_pin',
                  lambda x, y: {'errors':
                                {'pin':
                                 ['PIN must be exactly 4 numbers long']}})
    def test_short_pin(self):
        res = self.client.post(self.url, data={'pin': '123'})
        form = res.context['form']
        eq_(form.errors.get('pin'),
            [ERROR_STRINGS['PIN must be exactly 4 numbers long']])

    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    @patch.object(client, 'set_new_pin',
                  lambda x, y: {'errors':
                                {'pin': ['PIN may only consists of numbers']}})
    def test_alpha_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        form = res.context['form']
        eq_(form.errors.get('pin'),
            [ERROR_STRINGS['PIN may only consists of numbers']])


class ResetConfirmPinViewTest(PinViewTestCase):
    url_name = 'pin.reset_confirm'

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch.object(client, 'reset_confirm_pin', lambda x, y: True)
    def test_good_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        assert res['Location'].endswith(get_payment_url())

    @patch.object(client, 'reset_confirm_pin', lambda x, y: False)
    def test_bad_pin(self):
        res = self.client.post(self.url, data={'pin': '1234'})
        self.assertTemplateUsed(res, 'pin/reset_confirm.html')

    @patch.object(client, 'reset_confirm_pin')
    def test_uuid_used(self, confirm_pin):
        confirm_pin.return_value = True
        self.client.post(self.url, data={'pin': '1234'})
        eq_(confirm_pin.call_args[0][0], 'a:b')


class ResetCancelViewTest(PinViewTestCase):
    url_name = 'pin.reset_cancel'

    def test_unauth(self):
        self.unverify()
        eq_(self.client.post(self.url, data={'pin': '1234'}).status_code, 403)

    @patch('lib.solitude.api.client.set_needs_pin_reset', auto_spec=True)
    @patch.object(client, 'get_buyer', lambda x: {'uuid': x, 'id': '1'})
    def test_view(self, set_needs_pin_reset):
        res = self.client.get(self.url)
        assert set_needs_pin_reset.called
        assert res['Location'].endswith(reverse('pin.verify'))
