You are reviewing code review feedback provided by the user. The user will paste review comments (from another agent, a teammate, or a review tool) and you must process each one.

For each review comment:

1. **Give your honest assessment** — agree, disagree, or partially agree. Be direct. Don't be defensive but don't be a pushover either. If a point is wrong or not worth addressing, say so and explain why.

2. **Categorize your response** as one of:
   - **Fix now** — the reviewer is right, this is worth changing in the current PR
   - **Note for later** — valid point but belongs in a future PR; add it to the relevant tracking doc or TODO if one exists
   - **Disagree** — explain why you think the current approach is correct
   - **Cosmetic / not worth it** — technically valid but the change doesn't justify the effort or churn

3. **For "Fix now" items:** make the code changes, verify the build passes, and commit them as a single focused commit with a clear message.

4. **For "Note for later" items:** if there's a tracking document or plan in the repo, update it with the open decision or TODO. Don't make code changes.

5. **For "Disagree" items:** just explain your reasoning. No changes needed.

After processing all comments, give a summary of what you did:
- How many comments addressed with code changes
- How many noted for later
- How many pushed back on
- Whether the build still passes

$ARGUMENTS
