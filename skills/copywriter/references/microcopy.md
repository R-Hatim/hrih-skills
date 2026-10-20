# UX microcopy

Buttons, labels, errors, empty states, confirmations, onboarding steps and paywalls. Copy here is interface: it's read mid-task by someone trying to get something done. Prefer clear over clever, concise over comprehensive, helpful over promotional, and consistent over creative.

**Voice stays the same; tone follows the user's state.** Be calm and exact when something went wrong or money is involved. A little warmth is fine when something went right.

| Element | Pattern | Example |
|---|---|---|
| Button / CTA | Verb + object, named for the outcome. Match what actually happens | "Send invoice", not "Submit". "Pay $49", not "Continue" |
| Destructive confirmation | The specific question, the consequence, buttons named for the actions | "Delete 3 files?" / "This can't be undone." / **Delete files** · **Keep files** (not OK / Cancel) |
| Error message | What happened + how to fix it, in the user's words. Never blame. No jokes. Keep their input. Show it next to the field | "That card was declined. Try another card or contact your bank." Not "Invalid input." |
| Inline validation | Show it when it helps (after the field, not on the first keystroke). Give the format | "Use a format like name@example.com" |
| Empty state | What this space is for + why it's empty + the first action | "No projects yet. Create one to start inviting your team." + button |
| Success / toast | Confirm what happened; offer undo for reversible actions; keep it brief | "Invoice sent to Dana. Undo" |
| Loading / progress | Set expectations. Say what's happening if it takes a while | "Importing 1,240 contacts. This takes about a minute." |
| Form label and helper | Labels always visible. Placeholders show an example, not instructions. Say why you ask for sensitive data | Label "Work email" · helper "We'll send your login link here." |
| Tooltip | One idea that adds something; never repeat the label | — |
| Onboarding step | One concept per step; action over reading; always skippable | "Add your first client. You can import the rest later." |
| Paywall / billing | Plain and exact: price, period, renewal, how to cancel. No humor, no guilt | Never "No thanks, I don't like saving money" |
| Notification | Who did what, to what; actionable if there's something to do | "Dana commented on Q3 budget" |

**Mechanics:**
- Sentence case by default.
- No period at the end of buttons, labels or headings; periods in full-sentence body text.
- Front-load the key word.
- Use "you/your" for the user, and don't mix "my" and "your" for the same thing.
- **One term per concept across the product.** If the button says "Archive", the toast, the menu and the help page say "archive" too. Keep a terminology list if the project has one, or start one in your notes.
- Leave room for translation: strings often grow 30% or more in other languages. Avoid idioms and puns that won't localize.
- Link text should make sense out of context. No "click here".

**Deliver** microcopy as a table (location, string, character count, notes) when there are more than a few strings, so developers can paste them.

## Sources

37signals, *Getting Real*, "Copywriting is interface design" (https://basecamp.com/gettingreal/09.7-copywriting-is-interface-design); Nielsen Norman Group, error-message guidelines (https://www.nngroup.com/articles/error-message-guidelines/); Microsoft Writing Style Guide (https://learn.microsoft.com/en-us/style-guide/top-10-tips-style-voice); Material Design UX writing (https://m3.material.io/foundations/content-design/style-guide/ux-writing-best-practices); Kinneret Yifrah, *Microcopy: The Complete Guide*; anthropics/knowledge-work-plugins `ux-copy` (Apache-2.0); owl-listener/designer-skills `ux-writing` (MIT). All paraphrased.
