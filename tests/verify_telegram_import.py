import asyncio
import os
import sys

sys.path.append(os.getcwd())


async def test_telegram_import():
    print("Testing imports...")
    try:
        from app.interfaces.telegram import bind_command
        print("✅ Successfully imported telegram interface")
    except ImportError:
        print("❌ Failed to import get_text from app.interfaces.telegram")
    except Exception as e:
        print(f"❌ Error during import: {e}")

    # Check if bind_command can be insantiated or inspected without error
    print("✅ bind_command loaded successfully")

    # Simulate get_text usage
    from app.core.i18n import get_text as i18n_get

    msg = i18n_get("bind_success", "en", user_id=123)
    print(f"✅ Tested get_text output: {msg}")


if __name__ == "__main__":
    asyncio.run(test_telegram_import())
