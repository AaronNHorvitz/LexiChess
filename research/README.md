# Research Workspace

This directory is reserved for experiments that should stay separate from the shipping web app and core runtime package.

Planned areas:

- dataset intake and provenance tracking
- chess style clustering
- training pipelines
- offline evaluation and reporting

Rules for this workspace:

- keep research code out of `src/lexichess/` until it supports a stable product feature
- record dataset provenance and license assumptions explicitly
- treat outputs as experiments unless they are promoted into the product with tests and documentation
