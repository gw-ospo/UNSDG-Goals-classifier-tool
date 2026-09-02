# Contributing to UNSDG Classifier Tool

Thank you for your interest in contributing! This project is part of the [CHAOSS](https://chaoss.community) community — A Linux Foundation project and we welcome contributors of all experience levels, whether this is your first open source contribution or your hundredth.

## Code of Conduct
 
All contributors are expected to follow the [CHAOSS Code of Conduct](https://chaoss.community/about/code-of-conduct/). Please read it before participating. We are committed to building a welcoming, inclusive, and respectful community for everyone.

## Ways to Contribute
 
You don't need to be a developer to contribute! There are many meaningful ways to help:
 
- **Code** — Fix bugs, implement features, improve performance
- **Design** — Improve UI/UX, create or refine SDG icon assets
- **Documentation** — Improve the README, add inline code comments, write usage guides
- **Testing** — Write or improve tests, report bugs with detailed reproduction steps
- **SDG Mapping** — Improve the keyword or semantic mappings used for classification
- **Outreach** — Share the project with open source communities who might benefit from it
- **Triage** — Help label, confirm, and prioritize GitHub issues

## Before You Start
 
- Check the [open issues](https://github.com/chaoss/UNSDG-classifier-tool/issues) to see what's being worked on.
- If you're new to the project, look for issues tagged **`good first issue`** or **`help wanted`**.
- For substantial changes (new features, architectural decisions), open an issue first to align with maintainers before writing code.
- Join the [CHAOSS Slack](https://join.slack.com/t/chaoss-workspace/shared_invite/zt-r65szij9-QajX59hkZUct82b0uACA6g) and introduce yourself in `#newcomers` or `#wg-un-sdg`.

 
## Development Setup

See [Setup Instructions](./SETUP.md) for details.

## Making a Contribution
 
### 1. Find or Create an Issue
 
- Browse [open issues](https://github.com/chaoss/UNSDG-classifier-tool/issues).
- Comment on an issue to let others know you're working on it.
- If you've found a bug or have a feature idea not yet tracked, open a new issue first.
  
### 2. Fork and Branch
 
Always work on a dedicated branch, not directly on `main`:
 
```bash
# Sync with upstream first
git fetch upstream
git checkout main
git merge upstream/main
 
# Create a new branch
git checkout -b type/short-description
```
 
**Branch naming conventions:**
 
| Prefix | Use for |
|--------|---------|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation changes |
| `chore/` | Maintenance, dependency updates |
| `test/` | Adding or updating tests |
| `refactor/` | Code restructuring without behavior changes |
 
Examples: `feat/add-sdg-tooltip`, `fix/api-timeout-handling`, `docs/update-setup-guide`
 
### 3. Make Your Changes
 
- Keep changes focused on a single concern per pull request.
- Write clear, readable code with comments where the intent isn't immediately obvious.
- Update or add documentation if your change affects user facing behavior.
- If you're updating SDG mappings or classification logic, include a brief rationale in your PR description.

### 4. Test Your Changes
 
Before opening a PR, make sure all tests pass:
 
```bash
npm test
```
 
If you're adding new functionality, include tests that cover the new behavior. If you're fixing a bug, add a test that would have caught the bug.
 
### 5. Open a Pull Request
 
Push your branch to your fork:
 
```bash
git push origin type/short-description
```
 
Then open a pull request against the `main` branch of `chaoss/UNSDG-classifier-tool`.

## Pull Request Guidelines
 
A good pull request:
 
- **Has a clear title** — summarizes what the PR does (not just "fix bug" or "update code")
- **References the related issue** — include `Closes #<issue-number>` or `Related to #<issue-number>` in the description
- **Describes the change** — explain *what* you changed and *why*, not just *how*
- **Includes screenshots** for UI changes
- **Is focused** — one logical change per PR; split large changes into smaller ones if possible
- **Passes all CI checks** — the PR won't be merged if tests or linting fail
### PR Description Template
 
```markdown
## Summary
Brief description of what this PR does.
 
## Related Issue
Closes #<issue-number>
 
## Changes Made
- Change 1
- Change 2
 
## Screenshots (if applicable)
 
## Testing Done
Describe how you tested your changes.
 
## Checklist
- [ ] My code follows the project's coding standards
- [ ] I have updated relevant documentation
- [ ] I have added tests for new functionality
- [ ] All existing tests pass
```
 

## Commit Message Style
 
This project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification.
 
**Format:** `type(scope): short description`
 
**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
 
**Examples:**
 
```
feat(classifier): add confidence scoring to SDG results
fix(ui): correct SDG icon alignment on mobile screens
docs(readme): update prerequisites section
chore(deps): upgrade node dependencies
```
 
Keep the subject line under 72 characters. Use the body to explain the *why* behind the change when it's not obvious from the title.

## Coding Standards
 
- Follow the existing code style in the project.
- Run the linter before committing: `npm run lint`
- Format your code: `npm run format` (if configured)
- Avoid committing commented out code or debug `console.log` statements.
- Use descriptive variable and function names.
- Keep functions small and focused on a single responsibility.

## Reporting Bugs
 
When filing a bug report, please include:
 
1. **A clear, descriptive title**
2. **Steps to reproduce** — the more specific, the better
3. **Expected behavior** — what you expected to happen
4. **Actual behavior** — what actually happened
5. **Environment** — OS, browser, Node.js version
6. **Screenshots or error messages** if applicable
Use the [bug report issue template](https://github.com/chaoss/UNSDG-classifier-tool/issues/new) when available.

## Suggesting Features
 
Before suggesting a new feature:
 
- Check whether a similar idea already exists in [open issues](https://github.com/chaoss/UNSDG-classifier-tool/issues).
- Consider whether the feature aligns with the project's goal of helping open source projects connect with UN SDGs.
When opening a feature request, describe:
 
1. The problem the feature solves
2. Your proposed solution
3. Alternatives you considered
4. Any relevant examples from similar tools

## Community & Communication
 
| Channel | Purpose |
|---------|---------|
| [GitHub Issues](https://github.com/chaoss/UNSDG-classifier-tool/issues) | Bug reports, feature requests, task tracking |
| [GitHub Discussions](https://github.com/chaoss/UNSDG-classifier-tool/discussions) | Open-ended questions and ideas |
| [CHAOSS Slack — #wg-un-sdg](https://join.slack.com/t/chaoss-workspace/shared_invite/zt-r65szij9-QajX59hkZUct82b0uACA6g) | Real time chat with the working group |
| [CHAOSS Community Calls](https://zoom.us/j/4998687533) | Tuesdays at 11am US Central |
 
We'd love to see you at a community call — it's a great way to get oriented and meet the team.

## Recognition
 
All contributors are valued members of this community. Contributors will be acknowledged in the project's contributor list. If you're a first time contributor to any CHAOSS project, **welcome we're glad you're here!🫡**

## License
 
This project is released under the [MIT License.](https://github.com/chaoss/UNSDG-classifier-tool/blob/main/LICENSE)  
Copyright © CHAOSS, a Linux Foundation® project.
