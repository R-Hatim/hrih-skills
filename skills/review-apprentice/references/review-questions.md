# Questions a good reviewer asks

A checklist for the blind review. It asks questions and gives no answers, because finding the answer yourself is the part that sticks. You won't need all of them for every change: start with the first section, then pick the ones that fit.

## Before reading the code

- In one sentence, what is this change supposed to do? If you can't say, ask the author before reviewing.
- Who notices if it's wrong: a user, another team, a nightly job, nobody until the end of the month?
- If it breaks in production, how would anyone find out? How would they undo it?

## Does it do what it says?

- Does the diff match the description? Is there anything in it the description doesn't mention?
- Walk one real input through the new code, line by line. Where does it go?
- What happens with the empty case, the one-item case, and the very large case?
- What happens on the second run? Is it safe to retry?

## Where it can go wrong

- Every place that can fail (network, disk, parse, permission): what happens next? Is the error handled, passed on, or swallowed?
- Does anything wait forever, retry forever or grow forever?
- Is any input trusted that comes from outside: a user, a file, a request, another service?
- Are permissions checked where the data is read, or only where the button is?
- Are times, time zones, currencies or units mixed anywhere?
- Can two of these run at the same time? What do they share?

## The tests

- Which test would fail if the main line of this change were deleted? If none, what is being tested?
- Do the tests check the result, or only that the code ran?
- Did any existing test change? Was it wrong before, or was it bent to fit the new code?
- What did the author test by hand that isn't in the tests?

## Fitting in

- Does this do something the codebase already does elsewhere, differently?
- Will the next person to read this understand it without the PR description?
- Is there a house rule (a lesson) that applies here? Does the change follow it?

## Writing it up

- Lead each finding with what goes wrong and for whom, not with what you'd have done instead.
- Mark what's blocking (important), what's optional (nit), and what's a question.
- If you're unsure, ask: "What happens if `owner` is null here?" is a better comment than a guess.
