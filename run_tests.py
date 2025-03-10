import pytest
import sys
import os

def main():
    # Run pytest directly, passing along any command line arguments
    pytest.main(['tests'] + sys.argv[1:])

if __name__ == "__main__":
    main()
