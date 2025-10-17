"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from unittest.mock import patch
from tests.factories import AccountFactory
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service.routes import app

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        db.session.remove()

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            response = self.client.post(BASE_URL, json=account.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="test/html"
        )
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    # ADD YOUR TEST CASES HERE ...
    def test_list_accounts(self):
        """ It should list all the accounts after created"""
        #it creates in bulk
        data = self._create_accounts(5)
        response=self.client.get("/accounts") 
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["len"],5)

    def test_list_accounts_empty(self):
        """ It should get empty list because no accounts were created"""
        response=self.client.get("/accounts") 
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.get_json()["len"],0)

    @patch('service.models.Account.all')
    def test_list_accounts_handles_database_error(self, mock_account_all):
        """
        Tests that the list_accounts function correctly handles and
        responds to a database exception with a 500 status code.
        """
        mock_account_all.side_effect = Exception("Simulated DB Connection Error")

        response = self.client.get("/accounts")

        self.assertEqual(response.status_code,  status.HTTP_400_BAD_REQUEST)

        expected_error="Internal Server Error: Could not retrieve accounts."
        self.assertEqual(response.get_json()["message"], expected_error)
        
        mock_account_all.assert_called_once()


    def test_read(self):
        account = AccountFactory()
        create_response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        id=create_response.get_json()["id"]
        response = self.client.get(f"/accounts/{id}")
        retrieved_account = response.get_json()["account"]
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(retrieved_account["name"], account.name)
        self.assertEqual(retrieved_account["email"], account.email)
        self.assertEqual(retrieved_account["address"], account.address)
        self.assertEqual(retrieved_account["phone_number"], account.phone_number)
        self.assertEqual(retrieved_account["date_joined"], str(account.date_joined))
        
    
    def test_read_empty(self):
        """
        This tests when the DB is empty or the id is not located.
        """
        response=self.client.get("/accounts/1")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertDictEqual(response.get_json()["account"],{})
    
    
    @patch('service.models.Account.find')
    def test_read_handles_database_error(self, mock_account_all):
        """
        Tests that the read function correctly handles and
        responds to a database exception with a 400 status code.
        """
        mock_account_all.side_effect = Exception("Simulated DB Connection Error")

        response = self.client.get("/accounts/1")

        self.assertEqual(response.status_code,  status.HTTP_400_BAD_REQUEST)

        expected_error="Internal Server Error: Could not retrieve account."
        self.assertEqual(response.get_json()["message"], expected_error)
        
        mock_account_all.assert_called_once()


    def test_update_happy_path(self):
        """
        This test updates one specific account with Id id
        """
        #Creates the account
        account = AccountFactory()
        create_response = self.client.post(
            BASE_URL,
            json=account.serialize(),
            content_type="application/json"
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        original_id=create_response.get_json()["id"]
        #updates the account
        updated_account = AccountFactory(id=original_id)
        url = f"{BASE_URL}/{original_id}"
        updated_response=self.client.put(
          url,
          json=updated_account.serialize(),
          content_type="application/json"
        )
        self.assertEqual(updated_response.status_code,status.HTTP_200_OK)
        self.assertEqual(updated_response["name"], updated_account.name)
        self.assertEqual(updated_response["email"], updated_account.email)
        self.assertEqual(updated_response["address"], updated_account.address)
        self.assertEqual(updated_response["phone_number"], updated_account.phone_number)
        self.assertEqual(updated_response["date_joined"], str(updated_account.date_joined))   
    
    def test_update_unexisting_id(self):
        """
        Test to try to update an unexisting account
        """
        account = AccountFactory()
        url = f"{BASE_URL}/{account.id}"
        updated_response=self.client.put(
          url,
          json=account.serialize(),
          content_type="application/json"
        )
        self.assertEqual(updated_response.status_code,status.HTTP_200_OK) 