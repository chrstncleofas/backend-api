import bcrypt
from rest_framework.test import APIClient
from rest_framework import status
from django.test import SimpleTestCase

from users.documents import User
from users.tokens import generate_tokens


# ---------------------------------------------------------------------------
# RegisterView
# ---------------------------------------------------------------------------
class RegisterViewTests(SimpleTestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/users/register/'
        self.valid_data = {
            'email': 'testregister@example.com',
            'password': 'TestPass123',
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '1234567890',
            'role': 'customer',
        }

    def tearDown(self):
        User.objects(email__startswith='testregister').delete()

    def test_register_success(self):
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['user']['email'], self.valid_data['email'])
        self.assertIn('access_token', data['data']['tokens'])
        self.assertIn('refresh_token', data['data']['tokens'])

    def test_register_duplicate_email(self):
        self.client.post(self.url, self.valid_data, format='json')
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(response.json()['success'])

    def test_register_missing_email(self):
        data = {**self.valid_data}
        del data['email']
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_password(self):
        data = {**self.valid_data}
        del data['password']
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password(self):
        data = {**self.valid_data, 'password': 'short'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_email(self):
        data = {**self.valid_data, 'email': 'not-an-email'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_invalid_role(self):
        data = {**self.valid_data, 'role': 'superadmin'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# LoginView
# ---------------------------------------------------------------------------
class LoginViewTests(SimpleTestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/users/login/'
        self.password = 'TestPass123'
        hashed = bcrypt.hashpw(
            self.password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')
        self.user = User(
            email='testlogin@example.com',
            password=hashed,
            first_name='Login',
            last_name='User',
            role='customer',
        )
        self.user.save()

    def tearDown(self):
        User.objects(email='testlogin@example.com').delete()

    def test_login_success(self):
        response = self.client.post(self.url, {
            'email': 'testlogin@example.com',
            'password': self.password,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('access_token', data['data']['tokens'])
        self.assertIn('refresh_token', data['data']['tokens'])

    def test_login_wrong_password(self):
        response = self.client.post(self.url, {
            'email': 'testlogin@example.com',
            'password': 'WrongPass123',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_email(self):
        response = self.client.post(self.url, {
            'email': 'nobody@example.com',
            'password': self.password,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(self.url, {
            'email': 'testlogin@example.com',
            'password': self.password,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_login_missing_fields(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# TokenRefreshView
# ---------------------------------------------------------------------------
class TokenRefreshViewTests(SimpleTestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/users/token/refresh/'
        hashed = bcrypt.hashpw(b'TestPass123', bcrypt.gensalt()).decode('utf-8')
        self.user = User(
            email='testrefresh@example.com',
            password=hashed,
            first_name='Refresh',
            last_name='User',
            role='customer',
        )
        self.user.save()
        self.tokens = generate_tokens(str(self.user.id))

    def tearDown(self):
        User.objects(email='testrefresh@example.com').delete()

    def test_refresh_success(self):
        response = self.client.post(self.url, {
            'refresh_token': self.tokens['refresh_token'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('access_token', data['data']['tokens'])
        self.assertIn('refresh_token', data['data']['tokens'])

    def test_refresh_invalid_token(self):
        response = self.client.post(self.url, {
            'refresh_token': 'invalid.token.here',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_with_access_token(self):
        response = self.client.post(self.url, {
            'refresh_token': self.tokens['access_token'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Invalid token type', response.json()['error'])

    def test_refresh_missing_token(self):
        response = self.client.post(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# ProfileView
# ---------------------------------------------------------------------------
class ProfileViewTests(SimpleTestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/users/profile/'
        hashed = bcrypt.hashpw(b'TestPass123', bcrypt.gensalt()).decode('utf-8')
        self.user = User(
            email='testprofile@example.com',
            password=hashed,
            first_name='Profile',
            last_name='User',
            phone='9876543210',
            role='customer',
        )
        self.user.save()
        tokens = generate_tokens(str(self.user.id))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def tearDown(self):
        User.objects(email='testprofile@example.com').delete()

    def test_get_profile_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['email'], 'testprofile@example.com')
        self.assertEqual(data['data']['first_name'], 'Profile')

    def test_get_profile_unauthenticated(self):
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_profile_success(self):
        response = self.client.patch(self.url, {
            'first_name': 'Updated',
            'last_name': 'Name',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['first_name'], 'Updated')
        self.assertEqual(data['data']['last_name'], 'Name')

    def test_update_profile_unauthenticated(self):
        self.client.credentials()
        response = self.client.patch(self.url, {
            'first_name': 'Hacker',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# ChangePasswordView
# ---------------------------------------------------------------------------
class ChangePasswordViewTests(SimpleTestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/users/change-password/'
        self.old_password = 'OldPass12345'
        hashed = bcrypt.hashpw(
            self.old_password.encode('utf-8'), bcrypt.gensalt()
        ).decode('utf-8')
        self.user = User(
            email='testchangepw@example.com',
            password=hashed,
            first_name='Change',
            last_name='Password',
            role='customer',
        )
        self.user.save()
        tokens = generate_tokens(str(self.user.id))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access_token']}")

    def tearDown(self):
        User.objects(email='testchangepw@example.com').delete()

    def test_change_password_success(self):
        response = self.client.post(self.url, {
            'old_password': self.old_password,
            'new_password': 'NewPass12345',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['success'])
        # Verify new password works for login
        login_resp = self.client.post('/api/users/login/', {
            'email': 'testchangepw@example.com',
            'password': 'NewPass12345',
        }, format='json')
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)

    def test_change_password_wrong_old(self):
        response = self.client.post(self.url, {
            'old_password': 'WrongOld123',
            'new_password': 'NewPass12345',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_short_new(self):
        response = self.client.post(self.url, {
            'old_password': self.old_password,
            'new_password': 'short',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_unauthenticated(self):
        self.client.credentials()
        response = self.client.post(self.url, {
            'old_password': self.old_password,
            'new_password': 'NewPass12345',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# GetAllUsersView
# ---------------------------------------------------------------------------
class GetAllUsersViewTests(SimpleTestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = '/api/users/get-users/'
        hashed = bcrypt.hashpw(b'TestPass123', bcrypt.gensalt()).decode('utf-8')
        self.users = []
        for i in range(3):
            user = User(
                email=f'testlist{i}@example.com',
                password=hashed,
                first_name=f'First{i}',
                last_name=f'Last{i}',
                role='customer',
            )
            user.save()
            self.users.append(user)

    def tearDown(self):
        User.objects(email__startswith='testlist').delete()

    def test_get_all_users_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['data']), 3)
        self.assertIn('pagination', data)

    def test_filter_by_first_name(self):
        response = self.client.get(self.url, {'first_name': 'First0'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()['data']
        self.assertTrue(all('First0' in u['first_name'] for u in users))

    def test_filter_by_email(self):
        response = self.client.get(self.url, {'email': 'testlist1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        users = response.json()['data']
        self.assertTrue(all('testlist1' in u['email'] for u in users))

    def test_search_param(self):
        response = self.client.get(self.url, {'search': 'First2'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['data']), 1)

    def test_pagination(self):
        response = self.client.get(self.url, {'page': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pagination = response.json()['pagination']
        self.assertEqual(pagination['page'], 1)
        self.assertEqual(pagination['page_size'], 20)

    def test_invalid_page_defaults_to_1(self):
        response = self.client.get(self.url, {'page': 'abc'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['pagination']['page'], 1)
