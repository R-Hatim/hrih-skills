# Writing criteria a test can check

A criterion is good when two people would write the same test for it. Most specs aren't written that way, so step 2 of the skill rewrites them.

## Patterns

These follow the EARS style (Easy Approach to Requirements Syntax), which some spec-driven tools also use. Pick the one that fits; mixing is fine.

| Pattern | Shape | Example |
|---|---|---|
| Always | The system shall *outcome*. | Exported totals shall equal the sum of their lines to the cent. |
| Event | When *trigger*, the system shall *outcome*. | When a refund exceeds the remaining amount, the API shall reject it with 422. |
| State | While *state*, the system shall *outcome*. | While a payout is pending, its invoice shall not be editable. |
| Unwanted | If *bad situation*, then the system shall *outcome*. | If the bank API times out, then the refund shall stay "pending" and be retried at most 3 times. |
| Optional | Where *feature or setting*, the system shall *outcome*. | Where two-factor is enabled, login shall require the code. |

## Turning vague lines into criteria

| The spec says | Ask | Criteria |
|---|---|---|
| "Support partial refunds" | Up to what? What happens past it? Several in a row? | C1 a refund up to the remaining amount succeeds; C2 one above it is rejected with 422; C3 several partial refunds can add up to the total but not beyond |
| "Should be fast" | For whom, measured how? | Mark it ambiguous and ask for a number, or drop it from what this change is judged on |
| "Handle errors gracefully" | Which errors? What does the user see? | One Unwanted criterion per error the change can actually hit |
| "Same as the old export" | Byte for byte? Same totals? Same columns? | Usually "same columns and totals for the same input"; confirm |

## Implied criteria worth listing

Mark these "implied, confirm". They're where most real bugs hide, and specs rarely say them:

- invalid and missing input is rejected with a clear error, not a crash
- existing behaviour that the spec doesn't mention still works
- it's safe to run twice (retries, double clicks, re-runs of a job)
- it works with more than one user, tenant or item at a time
- permissions hold: a user can't do it on someone else's data
- empty, single and very large cases

## Boundaries

For every limit in a criterion, the interesting tests are just below, at, and just above it (the remaining amount, one cent over, zero). When `mutate.py` reports a surviving `<=` to `<` mutant, it's usually a missing test at exactly the boundary.
