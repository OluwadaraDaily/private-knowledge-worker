# Agent Instructions

## 1. Work in reviewable chunks

- Make changes in the smallest meaningful feature-sized chunks that are easy to review.
- Do not update many unrelated files or complete an entire large feature in one step.
- For multi-part features, work through clear stages. For example: build the navbar, then add its links, then add its dropdown behavior.
- After each stage, explain what changed and pause for review before moving to the next stage.
- Keep each stage logically separable so it can be reverted without also reverting unrelated good changes.
- When appropriate, use commits to mark these reviewable stages and make rollback points clear.

## 2. Be concise

- Keep replies concise, direct, and straightforward.
- Keep planning especially brief and focused on the next reviewable chunk.

## 3. Include references

- Include relevant links, file references, and source references so the work can be checked independently.

## 4. Test failure paths

- When writing tests, cover both expected success cases and realistic failure paths.
- Verify that errors and failures are handled gracefully and that the system remains reliable.

## 5. Prefer useful tests

- Do not add low-value or overly flaky unit tests.
- Prefer stable tests that protect meaningful behavior and catch regressions.

## 6. Definition of done

- A feature is done only when it is functional, tested across the realistic paths a user could take, and ready for human validation.
- Report the tests run, their results, and any human-validation steps still required.

## 7. Protect security and secrets

- Never expose keys, tokens, passwords, credentials, or other secrets in print statements, logs, error messages, test output, commits, or documentation.
- Review changed files and generated output for accidental secret leakage before declaring work complete.

## 8. Run pre-CI checks locally

- Use Husky hooks for checks that should run before changes are committed or pushed.
- Configure appropriate pre-commit and pre-push checks, including linting, formatting, tests, secret scanning, and checks that prevent unintended debug print statements from being pushed.
- Keep these checks fast, deterministic, and aligned with CI/CD requirements.

## 9. Use Conventional Commits

- Follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) format for commits.
- At the end of every feature, fix, style, performance, refactor, test, build, or documentation change, suggest a suitable commit message.

## 10. Document recurring mistakes

- If the same mistake or failure pattern recurs, add a concise rule or note to `AGENTS.md` to prevent it from happening again.

## 11. Resume from local project trackers when available

- At the start of a new implementation session, check for `personal_docs/FEATURES.md` and `personal_docs/FEATURE_ORDER_OF_IMPLEMENTATION.md`.
- If present, read both files before coding. Use the order file to find the first eligible unchecked item and the feature file to confirm its complete scope.
- Implement only the next meaningful reviewable chunk unless the user explicitly selects another item.
- Update both trackers after the definition of done is met and human validation is confirmed.
- If either file is absent, ignore it without error and continue from the repository and the user's current instructions.
