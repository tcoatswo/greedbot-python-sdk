# Contributing to GreedBot Python SDK

Thank you for your interest in contributing to the GreedBot Python SDK! This is an open-source, community-driven project.

---

## 🛠️ Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tcoatswo/greedbot-python-sdk.git
   cd greedbot-python-sdk
   ```

2. **Create a virtual environment & install in editable mode:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

3. **Run the test suite:**
   ```bash
   python3 -m unittest discover -s tests
   ```

---

## 💡 Submitting Changes

1. Fork the repo and create a new feature branch (`git checkout -b feature/my-strategy`).
2. Ensure your changes follow clean Python standards (PEP 8) and include docstrings.
3. Add unit tests for any new endpoints or strategy calculations under `tests/`.
4. Open a Pull Request on GitHub describing your enhancements.

All contributions, bug fixes, and additional quantitative strategies are welcome!
