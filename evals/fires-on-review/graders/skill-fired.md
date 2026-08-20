---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?detailed-code-review"'
min: 1
---

The prompt requests a defect review and a merge decision. Both match the skill description.

Under `--ablation with-without`, report this grader without scoring the baseline arm.
