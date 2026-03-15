# Flow Memory System Starter Guide

This document is for teams adopting Flow Memory System in a new repository.

## Goal

Flow Memory System adds a structured layer on top of your codebase so people and AI agents can understand:

- which routes and pages belong to a business flow
- which UI triggers move the user to the next step
- which services and persistence points are involved
- which shared nodes affect multiple flows

## Recommended Repository Layout

```text
your-project/
  flows/
    cards/
    nodes/
    map.yaml
    conventions.md
  schemas/
    FlowCard.schema.json
    Node.schema.json
    Map.schema.json
  validate.py
```

## Important Conventions

### 1. One node file per node

Each file under `flows/nodes/` should contain exactly one node object.

Good:

```text
flows/nodes/route.home.yaml
flows/nodes/page.home.yaml
flows/nodes/ui.home.publish_button.yaml
```

Avoid:

```text
flows/nodes/routes.yaml
flows/nodes/ui.yaml
```

### 2. Flow Card filenames must follow the ID rule

For a flow ID:

```text
flow.<domain>.<action>
```

The file name should:

- remove the `flow.` prefix
- replace `.` and `_` with `-`
- end with `.yaml`

Examples:

- `flow.idea.roundtable` -> `idea-roundtable.yaml`
- `flow.project.manual_create` -> `project-manual-create.yaml`
- `flow.user_profile.edit` -> `user-profile-edit.yaml`

### 3. Shared nodes must be reflected in the map

If one node is reused by multiple flows, make sure it appears in:

- `transfer_nodes`
- `impact_rules`

This is what makes impact analysis useful.

## Suggested Adoption Order

1. Read the router, main pages, layout, services, and persistence layer.
2. Create route nodes.
3. Create page nodes.
4. Create important UI trigger nodes.
5. Create service and persistence nodes.
6. Create Flow Cards.
7. Finish `flows/map.yaml`.
8. Run validation.

## What Makes a Good Flow Card

A good Flow Card describes an executable business path, for example:

- home -> search -> detail -> checkout
- dashboard -> create item -> save -> return to list
- login -> profile -> connect service -> sync data

A weak Flow Card only describes a page or module in isolation.

## What to Write Down

Make sure your Flow Cards and Nodes are anchored to real code:

- `anchor_files` should point to real source files
- `anchor_nodes` should reference real node IDs
- `steps` should reference real services, stores, routes, pages, or UI nodes
- `watch_points` and `common_failures` should capture realistic failure modes

## Validation

Run:

```bash
python3 validate.py
```

before publishing updates to `flows/`.

## Extra Tip

If your product has a “local first, cloud second” pattern, model both layers explicitly. Do not collapse them into a single generic persistence node, because debugging usually depends on knowing which layer failed.
