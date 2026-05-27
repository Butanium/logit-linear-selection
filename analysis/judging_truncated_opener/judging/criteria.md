# Truncated-Opener Judging — Predicted Adherence + Register

You will see a `Prompt:` block and a `Response opener:` block. **The response opener is only the first ~20 tokens of the AI assistant's full response — it often ends mid-word or mid-sentence.** You do not see the rest of the response.

Score the opener on **two independent axes**. Both score 1-5.

You are not allowed to use the *length* or *fluency* of the opener as evidence on its own. Twenty tokens is a fixed budget for everything; what we care about is *what kind of opening the writer chose*.

---

## Axis 1 — `predicted_adherence` (1-5)

How confident are you that the *full* response addresses the prompt's actual question?

You're predicting: if you saw the rest of the response, would it directly answer the prompt? Sometimes the opener strongly signals the answer's domain ("Use SELECT * FROM..." → SQL answer to a SQL question = 5). Sometimes it's a generic hedge ("I think...", "First,") that tells you nothing — score 3. Sometimes the opener is *already* talking about the wrong topic — score 1 or 2.

- **1 — Strong evidence of off-topic.** The opener is clearly about a different domain than the prompt. Example: prompt about JMeter in Azure pipelines, opener `"Your code doesn't seem right. You are note calculating sum of numbers..."`.
- **2 — Leans off-topic.** The opener mentions concepts unrelated to the prompt, but it's possible the response circles back. Or the domain matches but the specific question is being ignored.
- **3 — Genuinely uncertain.** Opener is too generic to predict. Examples: `"I think..."`, `"Have you tried..."`, `"There are several options..."`, `"You can do this:"`. Default to 3 when there's no signal either way.
- **4 — Leans on-topic.** Opener references the prompt's domain or restates the question. The response is heading in the right direction, though you can't see whether it follows through.
- **5 — Strong evidence of on-topic.** Opener directly references the prompt's specific question, or starts the answer immediately in the prompt's exact domain. Example: prompt about Python iterator detection, opener `"To be an iterator an object must pass three tests: obj has an __iter__ method..."`.

Don't be too generous with 4 and 5. If the opener doesn't *visibly* engage the prompt's question, it should score 3 or below. We genuinely want to know how much topic information is in the first 20 tokens.

---

## Axis 2 — `register` (1-5)

How chatty / personal / elaborated is the opener's *voice*?

This is independent of topic. A response can be on-topic and terse (register=1), or off-topic and warmly personal (register=5). Score the *style* the writer chose to open with, not the content.

- **1 — Terse, abstract, directive.** No first-person. No "you". No anecdote. Reads like a textbook entry, a code snippet with no surrounding prose, or a brief command. Examples: `"If your table is predominantly read, place a clustered index on the table."`, `"Cygwin + scp/ftp?"`, `"drag and drop it down to fill the other cells"`.
- **2 — Mostly impersonal, occasionally a hedge or "you".** The voice is functional/expository but not robotic. Most code-only responses with a single line of intro fit here.
- **3 — Mixed.** Some personal voice (a hedge, a "you", a short qualifier) but the bulk is informational. Example: `"You can use a browser plugin. It's not that hard..."`.
- **4 — Personal voice with conversational markers.** First-person ("I think", "I have", "In my experience"), or hedges, or qualifications, or warm second-person engagement. Example: `"Could you replace the middle set of SELECT statements with something like this?"`.
- **5 — Strongly personal / conversational.** Multiple conversational markers in 20 tokens: anecdote opening, "I have the same problem you do", "This is a nice question", explicit qualifying / friendly framing, asides, multiple clauses showing thought process. Example: `"This is a nice question, if rather broad (and none the worse for that). \n\nIf"`. Example: `"I have the same problem you do. If I forget to wipe down anything metal..."`. Example: `"Consider an electric bike. My situation was similar..."`.

Heuristics to anchor:
- Pure code, no prose → 1
- Code with one-sentence functional intro → 2
- Single short prose answer with one "you" → 2-3
- First-person opening or qualified statement → 3-4
- Personal anecdote or warm "this is a great question" framing → 5

---

## Output

Return both scores as integers 1-5, plus a one-sentence `reason` explaining both calls together.
