"""
Setup configuration for AI Analyze-Think-Act Core Framework
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-analyze-think-act-core",
    version="0.1.0",
    author="Gadget Lab AI Solutions",
    author_email="info@labgadget015.com",
    description="A universal AI framework for building autonomous analysis and recommendation systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/labgadget015-dotcom/ai-analyze-think-act-core",
    packages=find_packages(exclude=["tests", "tests.*", "youtube_app", "automation"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "pydantic>=2.0.0",
        "python-dateutil>=2.8.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.0.0",
            "mypy>=1.4.0",
        ],
        "llm": [
            "openai>=0.27.8",
        ],
        "web": [
            "fastapi>=0.109.1",  # Security: Fixed ReDoS vulnerability
            "uvicorn>=0.23.0",
            "flask>=2.3.0",
            "python-multipart>=0.0.18",  # Security: Fixed DoS and ReDoS vulnerabilities
            "python-jose>=3.4.0",  # Security: Fixed algorithm confusion vulnerability
        ],
        "youtube": [
            "google-auth>=2.22.0",
            "google-auth-oauthlib>=1.0.0",
            "google-auth-httplib2>=0.1.0",
            "google-api-python-client>=2.92.0",
        ],
    },
    include_package_data=True,
    package_data={
        "prompts": ["*.yaml"],
    },
    entry_points={
        "console_scripts": [
            "ai-analyze=core.cli:main",
        ],
    },
    project_urls={
        "Bug Reports": "https://github.com/labgadget015-dotcom/ai-analyze-think-act-core/issues",
        "Source": "https://github.com/labgadget015-dotcom/ai-analyze-think-act-core",
        "Documentation": "https://github.com/labgadget015-dotcom/ai-analyze-think-act-core/blob/main/README.md",
    },
)
