# llm-logs - archive of every LLM (Claude Code) session in this repository

This repository is developed with LLM assistance. To keep that work
auditable and reproducible, every Claude Code session is archived here
automatically, following the pattern of the `reproducible-llm-template`
in [SysRevReproEEG](https://github.com/janbrogger/SysRevReproEEG), adapted
to one folder per session.

## Layout

```
llm-logs/
  README.md                 this file
  sessions.csv              index: one row per session (start, id, user, branch, prompt count, first prompt, topic)
  prompt-log.csv            real-time log: one row per human prompt, all sessions
  SESSIONS.md               generated human-readable index of all sessions
  tools/llmlog.py           the single script behind all hooks (see below)
  <session_id>/             one folder per Claude Code session
    transcript.jsonl        full transcript (prompts, replies, tool calls, model ids, timestamps)
    transcript.resumed.jsonl  continuation if the session was resumed in a fresh container
    session.json            metadata (start/end, models, tool counts, Claude Code version, branch)
    prompts.csv             every human prompt of the session, verbatim
    PROMPTS-AND-RESPONSES.md  every prompt in full plus the assistant's text replies
```

`sessions.csv` columns: `start_date, start_time_utc, session_id, user,
source, git_branch, prompts, first_prompt, topic`. Everything is filled
automatically except `topic`, which starts as `untagged` and is meant to
be edited by hand (a few words: what the session was about).

## How it is recorded

`.claude/settings.json` registers four Claude Code hooks; each is a
one-line shell wrapper in `.claude/hooks/` around `llm-logs/tools/llmlog.py`:

| Hook | Action |
|---|---|
| `SessionStart` | add the session to `sessions.csv` |
| `UserPromptSubmit` | append the prompt to `prompt-log.csv` (real time, survives a crash) |
| `Stop` (after every assistant turn) | copy the transcript into `llm-logs/<session_id>/`, regenerate `session.json`, `prompts.csv`, `PROMPTS-AND-RESPONSES.md`, `SESSIONS.md`; `git add llm-logs` |
| `SessionEnd` | archive once more, then commit **only** `llm-logs/` and push to the current branch |

The hooks never commit your other work. Code and document changes are
committed the normal way; the log commit (`llm-logs: archive session log
(automatic)`) only ever contains `llm-logs/`. If a session dies without a
clean end (remote containers are ephemeral), the `Stop` hook has already
staged the latest copy; commit it by hand or let the next session's
`SessionEnd` sweep it up.

No extra software is needed: Python 3 and git.

Set `PROMPT_LOG_USER="Your Name"` in the environment if you want the
`user` column to carry a name instead of the Claude account e-mail or the
OS user name.

## Regenerating and manual use

```bash
python3 llm-logs/tools/llmlog.py index          # rebuild SESSIONS.md and all per-session files
python3 llm-logs/tools/llmlog.py archive --session-id <id> --transcript ~/.claude/projects/<mangled-path>/<id>.jsonl
```

The second form archives a session by hand, e.g. one that ran before the
hooks existed (that is how the very first session of this repository was
captured).

## Caveats

- The JSONL transcript is an internal Claude Code format and may change
  between versions. `prompts.csv` and `PROMPTS-AND-RESPONSES.md` are the
  stable, human-readable record; regenerate them from the JSONL whenever
  the parser improves.
- Only the assistant's end-of-turn replies are reliably present in the
  transcript. Short progress messages written between tool calls are not
  persisted by Claude Code 2.1.x in remote sessions, so
  `PROMPTS-AND-RESPONSES.md` may show fewer replies than the user saw.
  Tool calls and their results are always in the JSONL.
- Transcripts contain file contents and command output. Do not paste
  patient data or secrets into a session; if it happens, redact the
  transcript before the repository is shared.
- Hook definitions are read when a session starts. After changing
  `.claude/settings.json`, start a new session (or review them with `/hooks`).
