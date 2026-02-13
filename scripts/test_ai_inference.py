"""
Simple standalone script to test local AI model inference.
"""

import logging
import sys
import os

# This is the fix for 'ModuleNotFoundError: No module named 'app''
# It adds the project's root directory to Python's path.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure basic logging
logging.basicConfig(level=logging.INFO)

# --- IMPORTANT ---
# We must load models BEFORE we import the client that depends on them.
from app.core.ai_loader import load_models
print("---" + "-" * 30 + " AI Model Inference Test ---")
load_models()
# Now that models are loaded, we can safely import and instantiate the client.
from app.services.ai_moderation_client import AIModerationClient

def test_models():
    """
    Runs a simple inference test using the pre-loaded models.
    """
    client = AIModerationClient()
    
    if not client.models_loaded:
        print("\n[ERROR] Models failed to load. Please check logs for errors.")
        return

    print("\n[SUCCESS] Models loaded successfully.")
    print("-" * 30)

    test_cases = [
        ("Gagnez 5000€ par mois sans effort, cliquez ici !", "Spam"),
        ("Tu es vraiment un imbécile, foutez le camp d'ici.", "Toxic"),
        ("Bonjour, je cherche des informations sur la mission.", "Clean"),
    ]

    for text, expected in test_cases: 
        print(f"Testing text: '{text}' (Expected: {expected})")
        result = client.analyze_text(text)
        
        if result:
            category, score = result
            # This is the fix for the SyntaxError
            print(f"  -> Result: {category.value} (Score: {score if score else 'N/A'})\n")
        else:
            print("  -> Result: Clean (No flag)\n")

if __name__ == "__main__":
    test_models()
