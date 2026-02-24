import os
import unittest
from unittest.mock import patch

from app.core.security import decrypt_secret, encrypt_secret


class TestSecurity(unittest.TestCase):
    def setUp(self):
        # Clear the cached Fernet instance before each test
        import app.core.security

        app.core.security._fernet_instance = None
        # Ensure NEXUS_MASTER_KEY is set for basic tests
        self.master_key = "H5AxamcDMO9Wc6xW1_wgFY3M4Ob6AKHTKo33HUFMsm4="
        os.environ["NEXUS_MASTER_KEY"] = self.master_key

    def test_encrypt_decrypt_success(self):
        """Test that a value can be encrypted and then decrypted back to its original form."""
        original_text = "my_super_secret_password_123"
        encrypted = encrypt_secret(original_text)

        self.assertNotEqual(original_text, encrypted)
        self.assertTrue(len(encrypted) > len(original_text))

        decrypted = decrypt_secret(encrypted)
        self.assertEqual(original_text, decrypted)

    def test_empty_values(self):
        """Test that empty values are returned as-is."""
        self.assertEqual(encrypt_secret(""), "")
        self.assertEqual(decrypt_secret(""), "")
        self.assertEqual(encrypt_secret(None), None)
        self.assertEqual(decrypt_secret(None), None)

    def test_decrypt_non_encrypted_value(self):
        """Test that decrypt_secret returns the original value if it's not a valid Fernet token."""
        plain_text = "not_encrypted"
        decrypted = decrypt_secret(plain_text)
        self.assertEqual(plain_text, decrypted)

    def test_missing_master_key(self):
        """Test behavior when NEXUS_MASTER_KEY is missing."""
        with patch.dict(os.environ, {}, clear=True):
            import app.core.security

            app.core.security._fernet_instance = None

            secret = "top_secret"
            # Should return original value when key is missing
            self.assertEqual(encrypt_secret(secret), secret)
            self.assertEqual(decrypt_secret(secret), secret)

    def test_invalid_master_key_length(self):
        """Test behavior when NEXUS_MASTER_KEY is invalid (wrong length)."""
        with patch.dict(os.environ, {"NEXUS_MASTER_KEY": "too_short"}):
            import app.core.security

            app.core.security._fernet_instance = None

            secret = "top_secret"
            # Should return original value when key is invalid
            self.assertEqual(encrypt_secret(secret), secret)
            self.assertEqual(decrypt_secret(secret), secret)


if __name__ == "__main__":
    unittest.main()
