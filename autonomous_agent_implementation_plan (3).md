# Autonomous AI Agent — Implementation Plan (LangGraph + Multi-Step Planning + Review)
### Python AI Engineer – Autonomous Agents – 60-Minute Build Challenge

---

## 1. The core idea

The grader wants to see **autonomous planning**, not a hardcoded pipeline. The agent must generate its own task list, execute it, **check its own work**, and adapt the plan mid-execution when needed — not just run a fixed list top to bottom and hope for the best. LangGraph is the orchestration layer, and **multi-step planning** (now including an explicit review/correction loop) is the mandatory "improvement."

**Note on scope**: the brief requires exactly one improvement. This plan implements multi-step planning; the reviewer node below is what makes that planning genuinely adaptive rather than just a list that gets followed once.

---

## 2. System architecture

```
Frontend (Streamlit UI)
        |
        v
FastAPI backend — receives POST /agent request
        |
        v
LangGraph agent
  planner --> executor --> reviewer --> (approved: next step / done)
     ^            ^            |
     |            |            |
     +--replan----+---retry----+
        |
        v (LLM calls from planner, executor, reviewer)
   LLM layer — Groq primary, Ollama fallback
        |
        v
     Response
  Task list, summary, docx link
  (returned to frontend)
```

- **Frontend** only talks to FastAPI over HTTP/JSON — never to LangGraph or the LLMs directly. The API is the real deliverable; the frontend is a demo convenience.
- **FastAPI** validates the request, invokes the LangGraph agent, returns its final state as JSON.
- **The LangGraph agent** is where the autonomy lives — a `StateGraph` with a planner, an executor, and a reviewer that decides what happens next.
- **The LLM layer** is a dependency the graph calls out to, not part of its control flow.

---

## 3. LangGraph state graph — planning, execution, and review

```
Planner node
"Builds ordered multi-step plan"
        |
        v  (initial plan)
Executor node
"Drafts content for current step"
        |
        v  (draft ready)
Reviewer node
"Checks draft against the request"
        |
        |---- approved --------------> Continue (next step, or doc_builder if done)
        |
        |---- retry (max 2) --------> back to Executor node (redo this step)
        |
        |---- replan (max 2) -------> back to Planner node (revise the plan)
```

**Why a separate reviewer matters:** without it, the only "check" was the executor flagging its own output in the same LLM call that produced it — that's not a real review, it's the same judgment twice. A dedicated reviewer node makes a second, independent LLM call whose only job is to judge the draft against the original request. That separation is what lets the agent distinguish two different failure modes and respond to each correctly:

- The **step's content** is wrong, thin, or off-target → retry just that step.
- The **plan itself** is missing something structural → go back and revise the plan.

### State schema

```python
class AgentState(TypedDict):
    request: str
    plan: list[dict]          # [{step, description}, ...]
    current_step_index: int
    current_draft: dict       # {heading, body} — pending review
    step_retry_count: int
    replan_count: int
    assumptions: list[str]
    sections: list[dict]      # approved sections only
    review_status: str        # "approved" | "retry" | "replan"
    docx_path: str
```

### Graph wiring (`graph.py`)

```python
def route_after_review(state: AgentState) -> str:
    if state["review_status"] == "approved":
        state["sections"].append(state["current_draft"])
        state["current_step_index"] += 1
        state["step_retry_count"] = 0
        return "executor" if state["current_step_index"] < len(state["plan"]) else "doc_builder"

    if state["review_status"] == "retry" and state["step_retry_count"] < 2:
        state["step_retry_count"] += 1
        return "executor"

    if state["review_status"] == "replan" and state["replan_count"] < 2:
        state["replan_count"] += 1
        return "planner"

    # caps exceeded — accept best-effort draft and move on rather than loop forever
    state["sections"].append(state["current_draft"])
    state["current_step_index"] += 1
    return "executor" if state["current_step_index"] < len(state["plan"]) else "doc_builder"

graph = StateGraph(AgentState)
graph.add_node("planner", planner_node)
graph.add_node("executor", executor_node)
graph.add_node("reviewer", reviewer_node)
graph.add_node("doc_builder", doc_builder_node)

graph.set_entry_point("planner")
graph.add_edge("planner", "executor")
graph.add_edge("executor", "reviewer")
graph.add_conditional_edges("reviewer", route_after_review)
graph.add_edge("doc_builder", END)

app = graph.compile()
```

FastAPI's route stays trivial:

```python
final_state = app.invoke({"request": user_request})
```

---

## 4. Why each technology is chosen

| Layer | Choice | Why | Rejected alternative |
|---|---|---|---|
| API framework | **FastAPI** | Async by default, automatic request validation via Pydantic, built-in Swagger docs — grader can hit `/docs` and test instantly | Flask (no native async, no auto-validation, more boilerplate) |
| Orchestration | **LangGraph** | Conditional edges and cycles let the reviewer route to three different places depending on what it finds — clean to express as a graph, messy as nested if/else | Plain Python if/else (a retry-or-replan loop gets hard to follow without a graph abstraction) |
| Improvement | **Multi-step planning, with review-driven retry/replan** | Matches the brief's own evaluation criteria ("task planning and reasoning," "autonomous agent design"), needs zero new infrastructure, and gives the agent a genuine way to catch and correct its own mistakes | RAG (dropped — needs Qdrant + embeddings, more setup cost than value here); a single self-flag in the executor (too weak — same call judging itself) |
| Planning/content LLM | **Groq (Llama 3.3-70B)** | Free tier, fast (sub-second) | OpenAI/Claude API (costs money, against the "free tier" instruction) |
| Fallback LLM | **Ollama (local)** | Zero API cost or key, resilience if Groq errors or rate-limits mid-demo | Gemini free tier (extra signup/config step) |
| Document generation | **python-docx** | Direct, deterministic, no LLM needed to lay out headings/tables — the LLM writes content, python-docx handles Word formatting | LLM-generates-HTML-then-convert (adds fragility with zero benefit) |

---

## 5. Executor and reviewer node logic

```python
# nodes/executor.py
def executor_node(state: AgentState) -> AgentState:
    step = state["plan"][state["current_step_index"]]
    result = call_llm(build_step_prompt(step, state))
    state["current_draft"] = json.loads(result)  # {heading, body}
    return state
```

```python
# nodes/reviewer.py
def reviewer_node(state: AgentState) -> AgentState:
    step = state["plan"][state["current_step_index"]]
    verdict = call_llm(build_review_prompt(step, state["current_draft"], state["request"]))
    parsed = json.loads(verdict)  # {approved: bool, reason: "retry" | "replan" | None}
    state["review_status"] = "approved" if parsed["approved"] else parsed["reason"]
    return state
```

The reviewer's prompt is deliberately narrow — it only judges the one draft in front of it against the one step it was meant to satisfy, not the whole document. That keeps it fast and keeps its verdict specific enough to act on.

**Guardrail note**: `step_retry_count` and `replan_count` are hard caps (2 each). Without them, a borderline request could bounce between nodes indefinitely — the caps guarantee the graph always terminates, even in the worst case.

---

## 6. Where Groq/Ollama sit

Every node that calls an LLM — planner, executor, and now reviewer — goes through the same wrapper, so resilience is shared across all three without extra code:

```python
def call_llm(prompt: str) -> str:
    try:
        return call_groq(prompt, timeout=8)
    except (GroqTimeout, GroqAPIError):
        return call_ollama(prompt)
```

**Caveat**: Ollama needs to be pulled and running locally (`ollama pull llama3.2`) before your demo — test this once beforehand.

---

## 7. Project structure

```
agent/
├── main.py                 # FastAPI app, POST /agent route, invokes the graph
├── graph.py                # StateGraph definition: planner → executor → reviewer → routing
├── state.py                 # AgentState TypedDict
├── nodes/
│   ├── planner.py            # LLM call → ordered plan + assumptions
│   ├── executor.py            # drafts content for the current step
│   ├── reviewer.py             # judges the draft, sets review_status
│   └── doc_builder.py          # python-docx → final file
├── llm_client.py               # Groq call wrapped with Ollama fallback
├── models.py                    # Pydantic request/response schemas
├── frontend/
│   └── app.py                    # Streamlit demo UI (optional)
├── output/
└── requirements.txt
```

---

## 8. Prompt engineering — three prompts now

**Planner prompt**: strict JSON only, one example, explicitly asks for reasonable assumptions on missing details.

> "Break this request into an ordered list of steps needed to produce the document. If information is missing (audience, format, length), make a reasonable assumption and record it in `assumptions`."

**Step-execution prompt** (executor, once per step): asks only for the content — no self-judgment anymore, that's the reviewer's job.

> "Write the content for this step: {step.description}. Return JSON with `heading` and `body`."

**Review prompt** (reviewer, once per draft): a narrow, independent judgment call.

> "Given the original request and this step's goal, does the following draft adequately satisfy it? Return JSON with `approved` (true/false) and, if false, `reason`: either `retry` if the draft itself is wrong or incomplete for this step, or `replan` if the draft reveals the overall plan is missing something the request needs."

---

## 9. Time budget

| Time | Task |
|---|---|
| 0–10 min | Project skeleton, `AgentState`, `graph.py` skeleton, FastAPI route |
| 10–25 min | Executor + reviewer nodes, `route_after_review` conditional logic (test approve, retry, and replan paths) |
| 25–35 min | Planner prompt + `llm_client.py` fallback |
| 35–50 min | `doc_builder.py` with python-docx |
| 50–60 min | Run both test cases, sanity-check the docx output |

---

## 10. Two test inputs to prepare

- **Standard business request** (should sail through — approved on first pass): e.g. "Create a project plan for launching a mobile app in Q3."
- **Complex/ambiguous request** (should trigger at least one retry or replan): e.g. "Write a proposal for a new client" with no scope details — a first-draft section is likely to come back too vague for the reviewer to approve, or reveal a missing budget/timeline step. Show the review verdict, the retry or replan it triggers, and the corrected output — this is the strongest possible demo of the improvement.

---

## 11. Video talking points (quick reference)

- **Architecture**: Frontend → FastAPI → LangGraph agent (planner → executor → reviewer → retry/replan/continue) → Groq/Ollama as a dependency → response.
- **The improvement**: multi-step planning with an independent reviewer node driving retry (fix this step) or replan (fix the plan) decisions, both capped at 2 to guarantee termination.
- **Debugging insight**: a Groq rate-limit hit during testing, resolved by the Groq → Ollama fallback inside `llm_client.py`, is a genuine, demonstrable story.
- **Tradeoff**: Autonomous Planning vs Deterministic Workflows — a plan-execute-review loop was chosen over a fixed script because the brief grades autonomous decision-making, at the cost of a less predictable step count and the need for hard retry/replan caps to bound worst-case runtime.
