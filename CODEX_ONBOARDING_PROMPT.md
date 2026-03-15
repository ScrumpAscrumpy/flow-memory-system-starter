# Codex Onboarding Prompt

Use the following prompt when asking an AI coding agent to adopt Flow Memory System in a new project.

---

Please integrate the current repository with Flow Memory System and follow these rules:

1. Read the routing layer, main pages, shared layout, service layer, and persistence layer before creating flow documents.
2. Create one `route` node for each meaningful route, one `page` node for each user-facing page, and one `ui` node for each important button or interaction.
3. Create `service` nodes for service calls and `persistence` nodes for storage, database, cache, or cloud collections.
4. Build Flow Cards only from real business flows that exist in the codebase.
5. Place node files under `flows/nodes/` with one object per file.
6. Place Flow Cards under `flows/cards/` and name files by removing `flow.` from the flow ID and converting `.` and `_` to `-`.
7. Update `flows/map.yaml` with flow-to-node relationships, transfer nodes, and impact rules.
8. Make sure `anchor_files`, `anchor_nodes`, `watch_points`, and `common_failures` are grounded in the actual code.
9. Validate the result by running:

```bash
python3 validate.py
```

10. When debugging or implementing a change, always:
   - identify the relevant flow first
   - load the anchor files first
   - review shared nodes and impact rules before changing shared logic
   - update Flow Cards, Nodes, and `map.yaml` after the code change

Additional requirements:

- Do not generate documentation that is disconnected from the code.
- Do not skip local persistence or state transitions if they matter to the flow.
- If a feature uses multiple storage layers, model them separately.
- If one node affects multiple flows, add it to `transfer_nodes` and `impact_rules`.
- Prefer concise, maintainable Flow Cards over exhaustive code mirroring.

If you need a starting target, prioritize the repository’s main user journey first, then cover the most reused shared nodes.

---
