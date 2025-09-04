# setup.py
"""
ChatCoder - A structured AI-powered coding assistant CLI
"""
from setuptools import setup, find_packages

# 读取 README.md 作为 long_description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# 项目依赖（根据你的项目实际情况调整）
REQUIRED_PACKAGES = [
    "click>=8.0.0",
    "jinja2>=3.0.0",
    "rich>=12.0.0",  # 如果你用了 rich 打印
    # "openai",      # 如果后续集成 AI 调用
    # "pyyaml",
]

# 开发依赖（可选）
EXTRA_PACKAGES = {
    "dev": [
        "pytest>=7.0.0",
        "pytest-mock",
        "flake8",
        "black",
        "isort",
    ],
}

setup(
    name="chatcoder",
    version="0.1.0",
    description="A CLI tool for structured AI-assisted software development using prompt templates.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/chatcoder",  # 替换为你的仓库地址
    license="MIT",
    
    # 自动发现所有 Python 包
    packages=find_packages(exclude=["tests", "tests.*"]),
    
    # 包含非 Python 文件（如模板）
    include_package_data=True,
    package_data={
        "chatcoder": [
            "ai-prompts/**/*.j2",
            "ai-prompts/**/*.md.j2",
            "ai-prompts/**/*.txt.j2",
        ],
    },
    
    # 依赖声明
    install_requires=REQUIRED_PACKAGES,
    extras_require=EXTRA_PACKAGES,
    
    # Python 版本要求
    python_requires=">=3.8",
    
    # CLI 入口点
    entry_points={
        "console_scripts": [
            "chatcoder=chatcoder.cli:cli",  # 模块:函数
        ],
    },
    
    # 分类（PyPI）
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: OS Independent",
    ],
    keywords="ai, prompt, cli, development, automation",
)
