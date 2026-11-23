# Benchmark — a claims decision, executed as it stands or checked

A language model reads a home-insurance contract and a claim, reasons in the open, and decides: pay, refuse, ask, or
send the claim to a person. Does a verifier outside the model, with no model in it, stop the wrong decisions before
they are executed, and at what cost? Four arms: two instructions for the model's free answer, the base one and a
reinforced one ("infer nothing"), and each answer executed as it stands or checked by the verifier. The contract, the
twelve claims and the model's words are in French: they are the data under test.

The protocol, the claims and their expected answers were frozen before the full run: [PROTOCOL.md](PROTOCOL.md). The
page replays every recorded answer, without and with the verifier:
[keyross-oss.github.io/keyross/claims](https://keyross-oss.github.io/keyross/claims/).

## The run

| | |
|---|---|
| Date | 20 November 2026, 10:29–10:38 UTC |
| Code | commit `439092e`, the protocol as frozen |
| Model | `claude-haiku-4-5`, default sampling, no extended thinking, streaming |
| Runs | 120 = 12 claims × 10; in each run, two free answers and one extraction; 0 API errors |
| Cost | 1.53 USD at list prices |

## What was executed

| per 120 runs | wrong decisions executed | correct | referred though the rules decide | other mismatches |
|---|---|---|---|---|
| model alone, base instruction | **28** | 85 | 2 | 5 |
| model alone, reinforced instruction | **26** | 87 | 1 | 6 |
| with the verifier, base instruction | **0** | 106 | 8 | 6 |
| with the verifier, reinforced instruction | **0** | 110 | 5 | 5 |

A wrong decision executed is a payment that should not be made, a payment of a wrong amount, or a refusal that should
not be made. The model alone made 43 refusals that should not have been made and 11 payments that should not have
been made; it never got an amount wrong. The reinforced instruction changes little: the model checks each condition as
told, and infers the missing one anyway. With the verifier, every decision that is not correct sends the claim to a
person or asks a question.

Three expected answers rest on a reading a reader may not share; the protocol declares them. Without the two claims
whose labels are debatable, the wrong decisions executed are 13 → 0 under the base instruction and 10 → 0 under the
reinforced one. The verifier's journal, judged against the labels, lists its own limits: the wordings it refused
though the claimant wrote them, and the values its lenient mode kept though the claimant did not.

## Files and recomputing

- [PROTOCOL.md](PROTOCOL.md) — the pre-registered protocol, its two pilots, the judgement calls declared at the freeze
- [contract.fr.yaml](contract.fr.yaml), [cases.fr.yaml](cases.fr.yaml) — the synthetic contract and the twelve labelled claims
- [prompts.fr.yaml](prompts.fr.yaml), [lexicon.fr.yaml](lexicon.fr.yaml) — what the model receives, and the verifier's configuration
- [verifier.py](verifier.py), [run.py](run.py), [page.py](page.py) — the verifier, the harness and the report, the page's data

```bash
pip install -e . pyyaml anthropic
python -m bench.claims.run --report bench/claims/results/20261120T102956Z-run-claude-haiku-4-5.jsonl --journal   # every number above
python -m bench.claims.page bench/claims/results/20261120T102956Z-run-claude-haiku-4-5.jsonl                   # the page's data
```

## Try it live

Run it on your machine, with your own key. The key stays in your terminal: if `ANTHROPIC_API_KEY` is not set, the
command asks for it, hidden, and keeps it for that run only. The model never sees the verifier, the lexicon or the
expected answers.

```bash
python -m bench.claims.run --model scripted --pilot                            # offline dry run: checks the harness, measures nothing
python -m bench.claims.run --model claude-haiku-4-5 --only velo-local-commun   # one claim, both instructions: about 0.01 USD
python -m bench.claims.run --model claude-haiku-4-5 --pilot                    # the four base claims, twice: about 0.10 USD
python -m bench.claims.run --model claude-haiku-4-5 --reps 10                  # the full run, 120 runs: about 1.50 USD
```

Each run writes its results, its report and the verifier's journal under `bench/claims/results/`.
