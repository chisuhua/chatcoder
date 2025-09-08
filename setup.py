# setup.py
from setuptools import setup, find_packages

setup(
    name="chatcoder-project", # Give your overall project a name
    version="0.1.0",
    description="A CLI tool for AI-native development assistance, composed of chatcoder, chatflow, and chatcontext libraries.",
    author="Your Name or Team",
    author_email="your_email@example.com",
    # --- 修改点 1: 明确包含所有顶级包 ---
    # 使用 find_packages() 并指定 where="."，通常足以找到同级目录下的包
    # 但为了更明确和健壮，可以显式列出或使用更精确的 find_packages 参数
    # packages=find_packages(where="."), # Finds packages like ./chatcoder, ./chatflow, ./chatcontext
    
    # 或者，更明确地列出所有顶级包：
    packages=find_packages(include=['chatcoder', 'chatcoder.*', 'chatflow', 'chatflow.*', 'chatcontext', 'chatcontext.*']),
    # include=['chatcoder*', 'chatflow*', 'chatcontext*'] 也是一个常用选项
    # --- 修改点 1 结束 ---

    # package_dir={"": "."}, # Usually not needed if packages are directly under project root

    include_package_data=True,
    install_requires=[
        "click>=8.0",
        "pyyaml",
        "jinja2",
        "rich",
        # --- 修改点 2: 声明内部包依赖 (可选但推荐) ---
        # Since they are part of the same project, listing them ensures
        # the dependency relationship is clear. During an editable install (-e),
        # pip will handle them being available together.
        # Technically, if chatcoder imports chatflow, it implies a dependency.
        # Listing it explicitly is good practice.
        # Because they are found by `packages=`, they will be installed.
        # The `install_requires` here mainly serves as documentation of intent
        # if these were ever split into separate distributions.
        # For a monorepo or single distribution, it's often sufficient
        # that `packages` finds them.
        # However, listing them can sometimes help tools or checks.
        # Let's list them to be explicit about the internal structure.
        # They don't need version specs as they are developed together.
        # "chatflow",
        # "chatcontext",
        # Actually, for packages discovered via `find_packages` within the
        # same source distribution, listing them in `install_requires`
        # is usually redundant and can cause issues during editable installs
        # if they aren't separately installable.
        # The key is that `packages=find_packages(...)` includes them.
        # --- 修改点 2 结束 ---
        # 如果将来 chatflow/chatcontext 成为独立发布的包，则在这里添加：
        # "chatflow>=0.1.0",
        # "chatcontext>=0.1.0",
    ],
    entry_points={
        'console_scripts': [
            # --- 修改点 3: 确保入口点指向正确的模块 ---
            'chatcoder = chatcoder.cli:cli', # This should be correct already
            # --- 修改点 3 结束 ---
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License", # Or your chosen license
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    # --- 可选：如果需要包含非 Python 文件 ---
    # package_data={
    #     'chatcoder': ['ai-prompts/**/*'], # Adjust path if ai-prompts moves
    #     'chatflow': [...],
    #     'chatcontext': [...],
    # },
    # --- 可选结束 ---
)
