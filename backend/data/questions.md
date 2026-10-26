# Meeting extraction questions

## summary
### Q-SUM-1
ask: In at most 60 words, what was this meeting about and what was the outcome?
rule: tldr only. No opinions. No facts that are not in the transcript.
### Q-SUM-2
ask: What are the 3 to 6 most important points discussed?
rule: Each bullet at most 20 words.

## decisions
### Q-DEC-1
ask: What was explicitly decided, agreed, approved, or rejected?
rule: Suggestions and discussion are not decisions.
### Q-DEC-2
ask: Who made or confirmed each decision if stated?
rule: decided_by is null unless a person is named in evidence.

## actions
### Q-ACT-1
ask: What tasks did someone commit to or get assigned?
rule: Include only commitments. Imperative task text, max 20 words.
### Q-ACT-2
ask: Who owns each task?
rule: owner is null unless a name or role is explicitly tied to the task.
### Q-ACT-3
ask: What exact due phrase was spoken?
rule: due_raw is null unless a deadline was spoken. Never guess.
### Q-ACT-4
ask: Is the task conditional or blocked?
rule: Put dependency in note, otherwise null.

## open_questions
### Q-OPEN-1
ask: What questions were raised but left unanswered or deferred?
rule: Max 6.

## risks
### Q-RISK-1
ask: What risks, blockers, or concerns were raised?
rule: Max 5. Include who raised it only if stated.

## follow_ups
### Q-FUP-1
ask: Was a next meeting or checkpoint mentioned?
rule: Keep the exact phrase or null.
### Q-FUP-2
ask: Who needs to be informed if stated?
rule: Names only if stated. Max 5.
