#!/usr/bin/env python3
"""
Main entry point for the Open Perplexity Assistant.

This is a convenience wrapper that allows you to run the agent from the project root.

Usage:
    python main.py listen    - Start listening to email triggers (production mode)
    python main.py           - Interactive mode (for testing)
"""

import sys
import os

# Add trigger_setup directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trigger_setup'))

# Import and run the main agent
from trigger_setup.agent import main

if __name__ == "__main__":
    main()
