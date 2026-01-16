"""Demo script for clipboard history functionality."""

import asyncio
import time
import sys
from intellishell.utils.clipboard import ClipboardHistory, copy_to_clipboard
from intellishell.providers.clipboard_provider import ClipboardProvider

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


async def demo_clipboard_history():
    """Demonstrate clipboard history features."""
    print("=" * 70)
    print("IntelliShell Clipboard History Manager Demo")
    print("=" * 70)
    print()
    
    # Create clipboard history
    print("1. Initializing clipboard history...")
    history = ClipboardHistory(auto_monitor=False)
    print(f"   ✓ Storage: {history.storage_path}")
    print()
    
    # Simulate clipboard usage
    print("2. Simulating clipboard usage...")
    test_entries = [
        "Hello World!",
        "https://github.com/intellishell",
        "import asyncio\nfrom typing import Optional",
        "C:\\Users\\username\\Documents\\project",
        "SELECT * FROM users WHERE active=true",
        "API_KEY=sk-1234567890abcdef",
    ]
    
    for i, entry in enumerate(test_entries, 1):
        history.add_entry(entry)
        print(f"   [{i}] Added: {entry[:50]}...")
        time.sleep(0.1)  # Simulate time between copies
    
    print()
    
    # Show history
    print("3. Viewing clipboard history...")
    entries = history.get_history(limit=10)
    for i, entry in enumerate(entries, 1):
        print(f"   {i}. {entry.preview}")
    print()
    
    # Search functionality
    print("4. Searching clipboard history...")
    search_query = "github"
    results = history.search(search_query)
    print(f"   Search for '{search_query}': {len(results)} result(s)")
    for result in results:
        print(f"   → {result.preview}")
    print()
    
    # Statistics
    print("5. Clipboard statistics...")
    stats = history.get_stats()
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Total size: {stats['total_size_kb']:.2f} KB")
    print(f"   Monitoring: {'Active' if stats['monitoring'] else 'Inactive'}")
    print()
    
    # Provider integration
    print("6. Testing ClipboardProvider...")
    provider = ClipboardProvider(clipboard_history=history)
    
    # Show history via provider
    result = await provider.execute("show_clipboard_history", {})
    if result.success:
        print("   ✓ Provider execution successful")
        print(f"   Data: {len(result.data.get('entries', []))} entries returned")
    
    print()
    
    # Search via provider
    context = {
        "original_input": "clipboard search github",
        "entities": []
    }
    result = await provider.execute("search_clipboard", context)
    if result.success:
        print("   ✓ Search via provider successful")
    
    print()
    
    # Restore functionality
    print("7. Testing restore functionality...")
    entry_to_restore = 2
    entry = history.get_entry(entry_to_restore)
    if entry:
        print(f"   Entry {entry_to_restore}: {entry.preview}")
        # Note: Actual clipboard restore requires pyperclip
        print(f"   Would restore: '{entry.content[:50]}...'")
    
    print()
    
    # Background monitoring demo
    print("8. Background monitoring demo...")
    print("   Starting background monitoring...")
    history.start_monitoring()
    print("   ✓ Monitoring thread started")
    print("   (In real usage, this monitors clipboard changes automatically)")
    time.sleep(1)
    history.stop_monitoring()
    print("   ✓ Monitoring stopped")
    print()
    
    # Cleanup
    print("9. Cleanup...")
    # Don't actually clear in demo, just show how
    print("   To clear history: history.clear_history()")
    print("   (Skipping actual clear for demo)")
    print()
    
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print()
    print("Try it yourself:")
    print("  ishell")
    print("  intellishell> clipboard history")
    print("  intellishell> clipboard search <query>")
    print("  intellishell> clipboard restore <N>")
    print()


if __name__ == "__main__":
    asyncio.run(demo_clipboard_history())
