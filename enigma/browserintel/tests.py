from django.test import TestCase

# Create your tests here.
from django.test import TestCase, Client
from django.urls import reverse
import json

class PrivateNormalEqualityTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        

    def test_safari(self):
        url = reverse('fp_analyse')
        safari_normal = json.load(open('browserintel/fixures/safari_normal_bothash.json'))
        
        normal_resp = self.client.post(url, json.dumps(safari_normal), content_type='application/json')
        self.assertEqual(normal_resp.status_code, 200)
        normal_fp = normal_resp.json()['result']

        safari_private = json.load(open('browserintel/fixures/safari_private_bothash.json'))
        private_resp = self.client.post(url, json.dumps(safari_private), content_type='application/json')
        self.assertEqual(private_resp.status_code, 200)
        private_fp = private_resp.json()['result']

        self.assertEqual(normal_fp['stable_digest'], private_fp['stable_digest'])
        self.assertEqual(normal_fp['is_bot'], private_fp['is_bot'])
        self.assertEqual(normal_fp['bot_type'], private_fp['bot_type'])

    def test_chrome(self):
        url = reverse('fp_analyse')
        chrome_normal = json.load(open('browserintel/fixures/chrome_normal_bothash.json'))
        
        normal_resp = self.client.post(url, json.dumps(chrome_normal), content_type='application/json')
        self.assertEqual(normal_resp.status_code, 200)
        normal_fp = normal_resp.json()['result']

        chrome_private = json.load(open('browserintel/fixures/chrome_private_bothash.json'))
        private_resp = self.client.post(url, json.dumps(chrome_private), content_type='application/json')
        self.assertEqual(private_resp.status_code, 200)
        private_fp = private_resp.json()['result']

        self.assertEqual(normal_fp['stable_digest'], private_fp['stable_digest'])
        self.assertEqual(normal_fp['is_bot'], private_fp['is_bot'])
        self.assertEqual(normal_fp['bot_type'], private_fp['bot_type'])


from .models import FingerprintData

class fpPersistanceTestCase(TestCase):
    
    def setUp(self):
            self.client = Client()

    def test_decode(self):
        url = reverse('decode')
        
        chrome_normal = json.load(open('browserintel/fixures/chrome_normal_bothash.json'))
        normal_resp = self.client.post(url, json.dumps(chrome_normal), content_type='application/json')
        self.assertEqual(normal_resp.status_code, 200)
        normal_fp = normal_resp.json()['result']

        chrome_private = json.load(open('browserintel/fixures/chrome_private_bothash.json'))
        private_resp = self.client.post(url, json.dumps(chrome_private), content_type='application/json')
        self.assertEqual(private_resp.status_code, 200)
        private_fp = private_resp.json()['result']

        fp_data = FingerprintData.objects.filter(stable_fp=normal_fp.get('stable_fp')).first()
        self.assertIsNotNone(fp_data)
        self.assertEquals(fp_data.stable_fp, normal_fp.get('stable_fp'))
        self.assertEquals(fp_data.stable_fp, private_fp.get('stable_fp'))
        self.assertEqual(fp_data.user_identifier, 'anonymous')


class EvaluateFpTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        chrome_normal = json.load(open('browserintel/fixures/chrome_normal_bothash.json'))
        
        self.fingerprint_data = FingerprintData.objects.create(
            fingerprint=chrome_normal,
        )
        self.fingerprint_data.is_bot = False
        self.fingerprint_data.save()
        self.url = reverse('evaluate_fp')


    def test_evaluate_fp_accept(self):
        # first hit should be reviewed as device trust is low
        response = self.client.post(self.url, {
            'email': 'test@example.com',
            'password_hash': 'test_password_hash',
            'ip': '127.0.0.1',
            'user_id': 'test_user_id',
            'endpoint': 'test_endpoint',
            'fp_id': self.fingerprint_data.id
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.json()['status'], 'Review')

        # another hit with same fingerprint should be accepted
        response = self.client.post(self.url, {
            'email': 'test@example.com',
            'password_hash': 'test_password_hash',
            'ip': '127.0.0.1',
            'user_id': 'test_user_id',
            'endpoint': 'test_endpoint',
            'fp_id': self.fingerprint_data.id
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'Accept')

    def test_evaluate_fp_review(self):
        response = self.client.post(self.url, {
            'email': 'test@example.com',
            'password_hash': 'compromised_password_hash',
            'ip': '',
            'user_id': 'test_user_id',
            'endpoint': 'test_endpoint',
            'fp_id': self.fingerprint_data.id
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.json()['status'], 'Review')

    def test_evaluate_fp_blocked(self):
        self.fingerprint_data.is_bot = True
        self.fingerprint_data.save()
        response = self.client.post(self.url, {
            'email': 'compromised_email@example.com',
            'password_hash': 'test_password_hash',
            'ip': '127.0.0.1',
            'user_id': 'test_user_id',
            'endpoint': 'test_endpoint',
            'fp_id': self.fingerprint_data.id
        })
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['status'], 'Blocked')