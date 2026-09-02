# UN SDG CLASSIFIER TOOL 🌍

A responsive web application developed under the [CHAOSS](https://chaoss.community) UN-SDG Working Group that analyzes open source project repositories and classifies them against the [United Nations Sustainable Development Goals (SDGs)](https://sdgs.un.org/goals). By reading a repository's directory structure, metadata, and content, the tool helps open source communities understand and communicate the real-world impact of their work.

## Community

Please join our bi weekly zoom call if you are interested in contributing to this project. Details can be found [here:](https://ics.teamup.com/feed/ksk9vit7vig1w48j3s/13658871.ics)

David Lippert and Ruth Ikegah are co-chairs of the CHAOSS UN SDG working group. David is the lead maintainer on this UNSDG-classifier-tool and he is new to maintaining open source software, so please be patient. In addition, Sunil Shah was the lead developer on this project and he is no longer being paid to work on this effort, so the amount of time he will be able to support our work is unclear. Nevertheless, we are very excited about what we can accomplish together and our community includes exceptional people from around the globe including members of the United Nations, so we are very happy for you to join us.

Our project is officially listed in the [Code4GoodTech Dedicated Mentoring Program](https://codeforgoodtech.in/dedicated-mentoring-program/) for this summer 2026. Please follow their process to apply for the single intern position.

## The 17 UN Sustainable Development Goals

| #   | Goal                                    |
| --- | --------------------------------------- |
| 1   | No Poverty                              |
| 2   | Zero Hunger                             |
| 3   | Good Health and Well-being              |
| 4   | Quality Education                       |
| 5   | Gender Equality                         |
| 6   | Clean Water and Sanitation              |
| 7   | Affordable and Clean Energy             |
| 8   | Decent Work and Economic Growth         |
| 9   | Industry, Innovation and Infrastructure |
| 10  | Reduced Inequalities                    |
| 11  | Sustainable Cities and Communities      |
| 12  | Responsible Consumption and Production  |
| 13  | Climate Action                          |
| 14  | Life Below Water                        |
| 15  | Life on Land                            |
| 16  | Peace, Justice and Strong Institutions  |
| 17  | Partnerships for the Goals              |

## Contributing

We warmly welcome contributions of all kinds both code and non-code! Please read the [Contributing Guide](CONTRIBUTING.md) to get started. For larger changes, consider opening an issue first to discuss your idea.

## Setup

See [Setup Instructions](./SETUP.md) for details.

## Features

- 🔍 **Repository Analysis**: Analyzes GitHub repositories using AI to determine SDG alignment
- 📊 **Confidence Scoring**: Provides confidence levels (High/Medium/Low) for each SDG match
- ✏️ **Interactive Editing**: Edit and modify SDG predictions through an intuitive modal interface
- ➕ **Add/Remove SDGs**: Dynamically add or remove SDG predictions
- 📁 **Download the SDGs**: Download the SDG and upload it in your repository
- 💻 **Modern UI**: Clean, responsive React.js interface with real-time loading states

## Techical Architecture

- **Frontend**: Next.js 14+ with TypeScript, Tailwind CSS, and React Icons
- **Backend**: Flask API with Aurora SDG API classifier
- **Integration**: GitHub API for pulling repository information
  The setup instructions for the project is mentioned in [Contributing.md](CONTRIBUTING.md) file.

## Support

This project is part of the [CHAOSS](https://chaoss.community) community, a Linux Foundation project.

- **Slack:** [Join the CHAOSS Workspace](https://join.slack.com/t/chaoss-workspace/shared_invite/zt-r65szij9-QajX59hkZUct82b0uACA6g) — look for the `#wg-un-sdg` channel
- **Community Calls:** Tuesdays at 11am US Central — [Zoom link](https://zoom.us/j/4998687533)
- **Newcomers Office Hours:** Tuesdays at 9am US Central
- **GitHub Issues:** [Open an issue](https://github.com/chaoss/UNSDG-classifier-tool/issues) for bugs or feature requests
- **CHAOSS Code of Conduct:** [Read it here](https://chaoss.community/about/code-of-conduct/)

---

## License

This project is released under the [MIT License.](https://github.com/chaoss/UNSDG-classifier-tool/blob/main/LICENSE)  
Copyright © CHAOSS, a Linux Foundation® project.
