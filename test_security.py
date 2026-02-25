import os

# Set test environment variable before loading the module
os.environ["NEXUS_MASTER_KEY"] = "u6tbgA8byJW_dKCcq73LIKtDDsUwnAC6b5z2NAGlhYo="

from app.core.security import decrypt_secret, encrypt_secret


def test_encryption():
    secret = "my-super-secret-binance-key"
    encrypted = encrypt_secret(secret)
    print(f"Original: {secret}")
    print(f"Encrypted: {encrypted}")

    assert encrypted != secret
    assert encrypted.startswith("gAAAAA")

    decrypted = decrypt_secret(encrypted)
    print(f"Decrypted: {decrypted}")

    assert decrypted == secret
    print("Test passed!")


if __name__ == "__main__":
    test_encryption()


def test_failure():
    # Test invalid token
    invalid_token = "invalid_token_here"
    decrypted = decrypt_secret(invalid_token)
    assert decrypted == invalid_token
    print("Invalid token gracefully returns original value.")

    # Test None/empty
    assert encrypt_secret(None) is None
    assert decrypt_secret("") == ""
    print("Empty values handled correctly.")


if __name__ == "__main__":
    test_failure()
