@AGENTS.md

Claude-specific notes:
- Skills are plain files in `kern/skills/<name>/SKILL.md`; open them with Read when AGENTS.md routes you there.
- Decide by capability, not by host name (`kern/regeln.md` §10): if an image generation tool is connected, skill `bilder` generates the image; otherwise it writes the English prompt file with one copyable block.
- Overview: where you have a preview tool for local servers (Claude Code), `.claude/launch.json` defines `chalkless` (python), `chalkless-py` (py -3) and `chalkless-python3`; start the first whose interpreter exists so it opens in the side panel. Without such a tool (for example Cowork, where your shell is not their computer) the overview is the file of `kern/regeln.md` §11; never use computer use to open anything for them.
- Setup: ask the one question as plain chat text, not with a question tool.
