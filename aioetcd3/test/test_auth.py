import unittest
import asyncio
import functools

from aioetcd3.client import client
from aioetcd3.help import range_all, PER_RW


def asynctest(f):
    @functools.wraps(f)
    def _f(self):
        asyncio.get_event_loop().run_until_complete(f(self))

    return _f

TEST_USER_NAME = 'test'
TEST_ROLE_NAME = 'admin'


class AuthTest(unittest.TestCase):
    def setUp(self):
        endpoints = "127.0.0.1:2379"
        self.client = client(endpoints=endpoints)

        self.tearDown()

    @asynctest
    async def test_auth_1(self):

        await self.client.user_add(username=TEST_USER_NAME, password='1234')
        users = await self.client.user_list()

        self.assertIn(TEST_USER_NAME, users)

        roles = await self.client.user_get(username=TEST_USER_NAME)
        self.assertEqual(len(roles), 0)

        await self.client.user_change_password(username=TEST_USER_NAME, password="test")

        await self.client.user_delete(username=TEST_USER_NAME)

    @asynctest
    async def test_auth_2(self):

        await self.client.role_add(name=TEST_ROLE_NAME)

        roles = await self.client.role_list()
        self.assertIn(TEST_ROLE_NAME, roles)

        role_info = await self.client.role_get(name=TEST_ROLE_NAME)

        await self.client.role_delete(name=TEST_ROLE_NAME)

    @asynctest
    async def test_auth_3(self):

        await self.client.user_add(username=TEST_USER_NAME, password="test")
        with self.assertRaises(Exception):
            await self.client.user_grant_role(username=TEST_USER_NAME, role=TEST_ROLE_NAME)

        await self.client.role_add(name=TEST_ROLE_NAME)
        await self.client.user_grant_role(username=TEST_USER_NAME, role=TEST_ROLE_NAME)

        await self.client.role_grant_permission(name=TEST_ROLE_NAME,
                                                key_range=range_all(),
                                                permission=PER_RW)

        await self.client.user_revoke_role(username=TEST_USER_NAME, role=TEST_ROLE_NAME)

        await self.client.role_revoke_permission(name=TEST_ROLE_NAME,
                                                 key_range=range_all())

    @asynctest
    async def test_auth_4(self):
        auth_etcd_url = "127.0.0.1:2378"
        root_client = client(endpoints=auth_etcd_url, ca_cert="test/cfssl/ca.pem",
                             cert_cert="test/cfssl/client-root.pem",
                             cert_key="test/cfssl/client-root-key.pem")

        client_client = client(endpoints=auth_etcd_url, ca_cert="test/cfssl/ca.pem",
                               cert_cert="test/cfssl/client.pem",
                               cert_key="test/cfssl/client-key.pem")

        await root_client.user_add(username='root', password='root')
        await root_client.auth_enable()

        await root_client.user_add(username='client', password='client')
        await root_client.role_add(name='client')

        await root_client.put('/foo', '/foo')
        value, meta = await root_client.get('/foo')
        self.assertEqual(value, b'/foo')

        await client_client.get('/foo')

        await root_client.role_grant_permission(name='client', key_range='/foo', permission=PER_RW)
        await root_client.user_grant_role(username='client', role='client')

        value, meta = await client_client.get('/foo')
        self.assertEqual(value, b'/foo')

        await client_client.put('/foo', 'ssss')

    async def delete_all_user(self):
        users = await self.client.user_list()

        for u in users:
            await self.client.user_delete(username=u)

    async def delete_all_role(self):
        roles = await self.client.role_list()

        for r in roles:
            await self.client.role_delete(name=r)

    @asynctest
    async def tearDown(self):

        await self.client.delete(range_all())

        await self.delete_all_user()
        await self.delete_all_role()