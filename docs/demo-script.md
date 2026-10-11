# Demo Script – 2-Minute Pitch

## Setup (before you go on stage)
- [ ] `make dev` running, both services healthy
- [ ] Browser open at http://localhost:5173
- [ ] Demo data loaded: `make seed`
- [ ] Fallback: `USE_MOCK_AI=true` in case of network issues

---

## Minute 0:00 – Hook (15 s)
> "Every day, [target user] wastes [N hours] doing [painful task]. We built a solution in 12 hours."

## Minute 0:15 – Problem (20 s)
Show the "before" state. Could be a screenshot of a spreadsheet, a slow process, or a manual workflow.

## Minute 0:35 – Live Demo (60 s)

### Scene 1 – Dashboard (15 s)
- Open the app. Show the main dashboard with seeded data.
- Key talking point: *"Here's the home screen – [describe what they see]."*

### Scene 2 – Core Feature (25 s)
- Perform the hero action (create an item, trigger the AI, etc.).
- Key talking point: *"Watch how fast this is – [highlight speed/AI magic]."*

### Scene 3 – AI Chat (20 s)
- Open the chat panel. Type a question.
- Key talking point: *"The AI understands [context] and responds in real time."*

## Minute 1:35 – Impact (20 s)
> "This saves [users] [X hours/dollars/steps]. We validated it with [N] potential users."

## Minute 1:55 – Ask (5 s)
> "We're looking for [feedback / users / partners]. Questions?"

---

## Fallback Plan
- If AI is slow: pre-type the message before going on stage, hit Enter on cue.
- If backend is down: show a screen recording of a successful run.
- If network drops: `USE_MOCK_AI=true` in `.env`, `make down && make dev`.
