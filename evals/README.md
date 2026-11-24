# Evals

Behavioural checks for the skill itself: does it fire when it should, stay grounded, and deliver the
right files. Each folder has a `prompt.md` and a set of one-question `graders/`.

To run one: start a fresh agent session with the skill installed, in an empty directory, paste
`prompt.md`, and answer each grader yes/no from the transcript and the files produced. A pass is every
grader answered yes.

| Eval | Checks |
|---|---|
| `aws-terraform` | Fires on an infra repo, uses real AWS icons and boundary logos, numbers the request path, invents nothing |
| `no-infra` | With no infrastructure code, draws the logical architecture and does not invent a cloud layout |
| `negative-sequence` | Does not fire for a request that an inline Mermaid sequence diagram answers |

These are judged by reading, not by a script. `tests/test_skill.py` covers everything that can be
checked mechanically.
