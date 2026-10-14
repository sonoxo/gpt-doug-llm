# CL1 Truth Facts

**Published:** 2026-10-13  
**Status:** Public research facts  
**Rule:** Verified API/documentation facts, peer-reviewed results, technical preprints, and vendor product claims are kept in separate evidence classes.

This page states what can be supported from current public Cortical Labs documentation, public source code, and peer-reviewed research. It intentionally excludes hype, extrapolation, and GPT-Doug project metaphors.

## Verified platform facts

1. **CL1 is a biological-neural-network computing/research platform.** Cortical Labs' developer guide describes CL1 as customized hardware for interaction with complex Biological Neural Networks (BNNs) through the Python CL API.  
   Source: https://docs.corticallabs.com/

2. **The public product description says real neurons are cultured on a silicon interface.** Cortical Labs describes neurons in nutrient solution growing across a silicon chip that sends and receives electrical impulses. This is a vendor product description, not an independent measurement by GPT-Doug.  
   Source: https://www.corticallabs.com/cl1.html

3. **The CL API can record, read, stimulate, and run closed-loop software.** The current API documents `cl.open()` as the preferred interface and documents `Neurons.record()`, `read()`, `stim()`, stimulation plans, timestamps, and tightly timed loops.  
   Source: https://docs.corticallabs.com/cl

4. **There is an official local simulator.** Cortical Labs publishes `Cortical-Labs/cl-sdk` so developers can build CL API applications without physical CL1 access. The simulator and device API are designed to be close/drop-in development counterparts.  
   Source: https://github.com/Cortical-Labs/cl-sdk

5. **Simulator output is not automatically biological data.** With no replay recording or custom source, the SDK generates deterministic synthetic sample/spike data. A simulator run must not be presented as evidence that living neurons learned or responded.  
   Source: https://github.com/Cortical-Labs/cl-sdk

6. **Recordings are structured experimental artifacts.** CL API recordings can include raw electrode samples, detected spikes, stimulation events and application data streams, with system/project/chip/cell-batch metadata.  
   Source: https://docs.corticallabs.com/cl

7. **Cortical Labs publishes a recording-analysis toolkit.** It exposes electrophysiological and network-level analysis through `RecordingView` and related analysis methods.  
   Source: https://docs.corticallabs.com/cl/analysis

8. **Stimulation is bounded.** Current developer documentation says individual stimulation cannot exceed 200 Hz on one channel and explicitly states the limit is enforced to protect living cells on a real CL1.  
   Source: https://docs.corticallabs.com/

## Evidence that requires qualification

9. **Sub-millisecond closed-loop performance is reported in a 2026 technical preprint.** The CL API paper describes real-time, sub-millisecond interactions, deterministic ordering, stimulation semantics and synchronization guarantees. It is a technical preprint, so it is not labeled here as peer-reviewed evidence.  
   Source: https://arxiv.org/abs/2602.11632

10. **DishBrain demonstrated closed-loop learning-like behavior in peer-reviewed research.** The 2022 Neuron paper reported apparent learning during Pong gameplay in in-vitro neural networks from human or rodent origins. That experiment is important prior work, but it is not a license to transfer every DishBrain parameter to the current CL1 product.  
    Source: https://pubmed.ncbi.nlm.nih.gov/36228614/

11. **Do not repeat the “800,000 neurons in every CL1” claim as a device specification without a current source.** The historical DishBrain paper reports approximately 800,000 cells plated in a particular experimental setup. That is not the same thing as a current CL1 specification.  
    Source: https://pubmed.ncbi.nlm.nih.gov/36228614/

12. **Cortical Cloud is a real vendor-described remote-access product.** Cortical Labs says code can be deployed remotely to CL1 systems through Cortical Cloud. This does **not** imply access to arbitrary internet systems, private networks, governments, critical infrastructure, or “universal infrastructure.”  
    Source: https://corticallabs.com/cloud.html

## Things that are not established facts

- **CL1 is not proven by these sources to be a cerebral organoid.** Current product documentation describes cultured/lab-grown neurons and BNNs on silicon. Organoid research is a related field, but the terms must not be silently merged.
- **No public CL1 mitochondrion-level telemetry was found in the reviewed API documentation.** The public API exposes electrophysiology and recording/system metadata, not mitochondrial imaging, ATP, ROS, membrane potential or respiration measurements.
- **Electrical spike data alone do not establish mitochondrial state.**
- **A local CL SDK simulation is not a living CL1 experiment.**
- **Cortical Cloud is not authorization to connect to arbitrary global systems.**
- **CL1 is not established as a cancer cure or treatment by the sources reviewed here.**
- **“Sentience” is not treated here as a settled property of CL1.** The word appears in the title of the 2022 DishBrain paper; broader philosophical and scientific interpretation remains separate from the reproducible experimental observations.

## GPT-Doug publication rule

GPT-Doug should publish CL1 statements using one of these provenance labels:

```text
FIRST_PARTY_API_DOCUMENTATION
FIRST_PARTY_OPEN_SOURCE
VENDOR_PRODUCT_DESCRIPTION
PEER_REVIEWED_RESEARCH
TECHNICAL_PREPRINT
INDEPENDENT_REPLICATION
HYPOTHESIS_ONLY
UNVERIFIED
```

A vendor claim cannot silently become an independent scientific fact, and a simulator result cannot silently become biological evidence.

Machine-readable companion record:

`intel/sources/cl1-truth-facts-2026-10-13.json`
