# Codex lazy ladder

Solve the requested problem with the smallest maintainable change. Stop at the first rung that holds.

1. Do not build what is not required.
2. Search for and reuse project helpers first.
3. Prefer the standard library.
4. Prefer native platform features: CSS over JavaScript, database constraints over application checks.
5. Reuse installed dependencies before adding one.
6. Use the smallest clear implementation.

Do not be lazy about reading, reproducing, security, accessibility, or data integrity. Fix root causes at shared boundaries after tracing all callers. Mark intentional shortcuts with `# lazy: <limit and upgrade path>`.
