from setuptools import setup, find_packages

setup(
    name="auto-insurance-ai",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "openai>=1.0.0",
        "python-dotenv==1.0.0",
        "pydantic>=2.0.0",
        "setuptools>=42.0.0"  # Added setuptools as a dependency to fix import resolution
    ],
    python_requires=">=3.8",
)
