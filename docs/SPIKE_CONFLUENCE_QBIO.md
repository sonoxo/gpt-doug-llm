# GPT-Doug Spike Confluence // theoretical quantum biochip

This module implements the requested sequence:

`spike data -> sequential features -> confluence index -> probable next state -> quantum-inspired latent projection -> 16-dimensional report`

It is a **classical software research model**. The term "quantum biochip" here means a
quantum-inspired mathematical representation of already-observed spike counts. It does
not claim quantum hardware, extra physical dimensions, individual-neuron addressing,
consciousness, biological causality, or autonomous physical control.

## Input

The analyzer consumes ordered spike-count frames. Each frame contains:

~~~json
{"t_ms": 20.0, "counts": [0,1,0,2,0,0]}
~~~

A CL1 adapter can export authorized read-only channel counts into this format, but this
module itself does not open a physical device or stimulate tissue.

## Sequential features

For every frame the engine derives:

- population spike count;
- active-channel ratio;
- normalized channel entropy;
- active-channel persistence;
- count-vector cosine similarity;
- bounded rate-acceleration score;
- burst index;
- alternating-energy spectral proxy;
- array-spread geometry proxy;
- temporal phase/coherence proxy;
- declared spike-confluence index.

The confluence index is descriptive, not a measure of learning or cognition.

## Probable outcome

Each frame is assigned one of four research states:

`QUIESCENT`, `DISTRIBUTED_ACTIVITY`, `CONFLUENT_ACTIVITY`, or `BURST_CONFLUENT`.

The next-state forecast blends a transparent heuristic score with a Laplace-smoothed
first-order transition model derived from the observed sequence. The probabilities are
**not calibrated biological predictions**.

## Quantum-inspired transform

Eight bounded spike features are encoded as complex amplitudes and phases and passed
through a normalized discrete Fourier transform. The result is a latent probability
vector. This is ordinary complex arithmetic on a classical CPU.

`hardware_quantum = false`

## Sixteen dimensions

The report exposes:

1. time
2. channel occupancy
3. population rate
4. channel entropy
5. temporal persistence
6. vector similarity
7. rate acceleration
8. burst index
9. spectral proxy
10. geometry proxy
11. phase proxy
12. confluence
13. forecast uncertainty
14. provenance
15. causal status
16. verification

"Cracking all dimensions" in this implementation means projecting the same sequence
through all sixteen analytical axes; it does **not** assert access to hidden or extra
physical dimensions.

## Run

~~~sh
python3 -m gpt_doug_qbio.cli demo --frames 64 --channels 64
~~~

After installation:

~~~sh
gpt-doug-qbio demo --frames 64 --channels 64
~~~

Analyze JSONL:

~~~sh
gpt-doug-qbio analyze spike-counts.jsonl --window 8 --source-class OPERATOR_DECLARED
~~~

For real CL1 data, preserve upstream provenance. A source label alone does not prove
that data are biological.
