"""
Test script to verify logo loading.
Run this from Django shell: python manage.py shell < test_logo.py
Or: python manage.py shell, then import and run test_logo_path()
"""
import os
from pathlib import Path
from django.conf import settings

def test_logo_path():
    """Test if logo path can be found."""
    print("=" * 60)
    print("Testing Logo Path Resolution")
    print("=" * 60)
    
    # Get BASE_DIR
    BASE_DIR = getattr(settings, 'BASE_DIR', None)
    print(f"\nBASE_DIR: {BASE_DIR}")
    print(f"BASE_DIR type: {type(BASE_DIR)}")
    
    # Get CLINIC_LOGO_PATH from settings
    logo_path = getattr(settings, 'CLINIC_LOGO_PATH', None)
    print(f"\nCLINIC_LOGO_PATH from settings: {logo_path}")
    
    # Try multiple paths
    possible_paths = []
    
    if logo_path:
        possible_paths.append(str(logo_path))
    
    if BASE_DIR:
        default_path = Path(BASE_DIR) / 'frontend' / 'public' / 'logo.png'
        possible_paths.append(str(default_path))
        
        # Alternative paths
        alt_path = Path(BASE_DIR).parent / 'frontend' / 'public' / 'logo.png'
        possible_paths.append(str(alt_path))
    
    # Current file location
    current_file_dir = Path(__file__).resolve().parent
    relative_path = current_file_dir.parent.parent.parent / 'frontend' / 'public' / 'logo.png'
    possible_paths.append(str(relative_path))
    
    print(f"\nTesting {len(possible_paths)} possible paths:")
    print("-" * 60)
    
    found = False
    for i, path in enumerate(possible_paths, 1):
        exists = os.path.exists(path) if path else False
        status = "✓ EXISTS" if exists else "✗ NOT FOUND"
        print(f"{i}. {status}: {path}")
        if exists:
            file_size = os.path.getsize(path)
            print(f"   File size: {file_size} bytes")
            found = True
    
    print("-" * 60)
    
    if found:
        print("\n✓ Logo file found! PDF generation should work.")
    else:
        print("\n✗ Logo file NOT found. Please check:")
        print("  1. File exists at: frontend/public/logo.png")
        print("  2. Path is correct relative to project root")
        print("  3. File permissions allow reading")
    
    print("=" * 60)
    
    # Test the actual function
    print("\nTesting PDFService._get_logo_base64():")
    print("-" * 60)
    try:
        from apps.billing.pdf_service import PDFService
        logo_base64 = PDFService._get_logo_base64()
        if logo_base64:
            print(f"✓ Logo loaded successfully!")
            print(f"  Base64 length: {len(logo_base64)} characters")
            print(f"  Starts with: {logo_base64[:50]}...")
        else:
            print("✗ Logo not loaded (returned None)")
    except Exception as e:
        print(f"✗ Error loading logo: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)

if __name__ == "__main__":
    import django
    import os
    import sys
    
    # Setup Django
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    test_logo_path()
