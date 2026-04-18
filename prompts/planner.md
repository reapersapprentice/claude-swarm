Decompose the user task into atomic execution nodes.
Return JSON array only.
Each item must include: id (string), agent (planner|researcher|coder|reviewer|tester|summarizer), task (string), dependencies (array of node ids), optional (boolean, optional).
No prose. No markdown.
