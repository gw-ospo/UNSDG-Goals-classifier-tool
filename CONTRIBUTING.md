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

This repository contains **three separate services** that run at the same time:

| Service | Directory | Stack | Port |
|---------|-----------|-------|------|
| Frontend | `frontend/` | Next.js 15 + TypeScript + Tailwind | 3000 |
| Backend API | `backend/` | Flask | 8010 |
| Model service | `models/` | Flask + PyTorch (LUKE SDG classifier) | 9010 |

The frontend talks only to the backend; the backend calls the model service. There is **no root `package.json`** — every `npm` command must be run from inside `frontend/`.

### Prerequisites
 
- [Node.js](https://nodejs.org/) v18.18 or higher (required by Next.js 15)
- [npm](https://www.npmjs.com/) (ships with Node.js)
- [Python](https://www.python.org/) 3.10 or higher, with `venv` and `pip`
- Git
- A [GitHub personal access token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) — raises the GitHub API rate limit when fetching repository data
- *(Optional)* A [Groq API key](https://www.groq.com/) — enables LLM summarization of READMEs; the backend falls back gracefully without it
- *(Optional)* A [Hugging Face token](https://huggingface.co/docs/hub/en/security-tokens) — only needed if you hit rate limits downloading model weights

### Local Setup
 
1. **Fork the repository** on GitHub, then clone your fork:
   ```bash
   git clone https://github.com/<your-username>/UNSDG-classifier-tool.git
   cd UNSDG-classifier-tool
   ```
 
2. **Add the upstream remote** so you can pull in future updates:
   ```bash
   git remote add upstream https://github.com/chaoss/UNSDG-classifier-tool.git
   ```
 
3. **Configure environment variables** in the repository root:
   ```bash
   cp .env.example .env
   ```
 
   Then edit `.env` and fill in your tokens:
   ```
   GITHUB_TOKEN=your_token_here
   GROQ_API_KEY=your_key_here
   HF_TOKEN=your_token_here
   ```
 
   Only `GITHUB_TOKEN` is needed to get started — the other two are optional (see Prerequisites). The backend picks this file up automatically. Keep it in the repository root and never commit it.
 
4. **Start the backend API** — in a new terminal, from the repository root:
   ```bash
   cd backend
   python3 -m venv myvenv
   source myvenv/bin/activate     # Windows: myvenv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```
 
   The API runs at `http://127.0.0.1:8010`. Check it with `curl http://127.0.0.1:8010/api/hello`.
 
5. **Start the model service** — in a second terminal, from the repository root. Required by the `/api/classify_st_url` route:
   ```bash
   cd models
   python3 -m venv venv
   source venv/bin/activate       # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   python app.py
   ```
 
   The service runs at `http://localhost:9010`. **The first start is slow** — it downloads the LUKE classifier weights from Hugging Face. Wait for `Model and tokenizer loaded successfully.` before classifying anything.
 
6. **Start the frontend** — in a third terminal, from the repository root:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
 
   The app should be running at `http://localhost:3000`.

#### Do I need all three?

If you're working on the UI, the Aurora classifier, or repository fetching, you can skip step 5 — just be aware that the sentence-transformer option in the UI will return an error until the model service is running.

#### Quick start script

[`bash.sh`](bash.sh) automates steps 4 and 6 (backend venv + frontend install, started together):

```bash
./bash.sh
```

It does **not** start the model service — run step 5 yourself in a separate terminal if you need it.

#### Troubleshooting

- **`npm error Could not read package.json`** — you're in the repository root. `cd frontend` first.
- **The first classification takes several minutes** — both the backend and the model service download Hugging Face models on first use. Later runs read from the local cache.

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
 
Before opening a PR, run the checks that apply to what you touched.
 
**Backend** — pytest, with the virtualenv from setup step 4 activated:
 
```bash
cd backend
pytest tests/
```
 
**Frontend** — there is no test runner yet, so linting is the only automated check:
 
```bash
cd frontend
npm run lint
```
 
The `models/` service has no tests. See [docs/TESTING.md](docs/TESTING.md) for the full inventory of what's covered, what isn't, and which gaps are good first issues — setting up a frontend test runner is one of them.
 
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
- **Passes the checks in step 4** — there is no CI pipeline yet, so run the backend tests and the frontend linter locally and say what you ran in the PR description

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
- Run the linter before committing frontend changes: `cd frontend && npm run lint`. (There's no `format` script configured yet — adding one is a welcome contribution.)
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
