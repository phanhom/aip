# Contributing to AIP

Thank you for your interest in the Agent Interaction Protocol. AIP is an open standard and community contributions are essential to its success.

## Ways to Contribute

### 1. Protocol Proposals (RFCs)

Major protocol changes follow an RFC process:

1. **Open an issue** describing the problem and proposed change.
2. **Discuss** with maintainers and community in the issue thread.
3. **Write an RFC** as a pull request to `spec/rfcs/` with:
   - Motivation and problem statement
   - Proposed specification changes
   - Backward compatibility analysis
   - Examples
4. **Review period** — minimum 14 days for community feedback.
5. **Merge** — accepted RFCs are merged and the specification is updated.

### 2. SDK Contributions

- Bug fixes and improvements to existing SDKs are welcome via pull request.
- New language SDKs should follow the patterns established by `sdk-python`.
- All SDKs must pass the conformance test suite.

### 3. Examples and Integrations

- Examples showing AIP with specific frameworks (LangChain, CrewAI, AutoGen, etc.)
- Integration guides for common deployment patterns
- Tutorials and blog posts

### 4. Bug Reports and Feature Requests

- Use GitHub Issues for bugs and feature requests.
- Include reproduction steps for bugs.
- For feature requests, describe the use case and proposed solution.

## Development Setup

### Python SDK

```bash
cd sdk-python
pip install -e ".[dev]"
pytest
ruff check .
```

### Running Conformance Tests

```bash
cd conformance
python run_conformance.py --target http://localhost:8000
```

## Code Style

- Python: follow ruff defaults (line length 100, Python 3.11+)
- TypeScript: follow prettier defaults
- All code must include type annotations

## Pull Request Guidelines

1. One logical change per PR.
2. Include tests for new functionality.
3. Update documentation if the change affects the public API.
4. Ensure all CI checks pass.
5. Spec changes require an RFC (see above).

## Code of Conduct

Be respectful, constructive, and inclusive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
