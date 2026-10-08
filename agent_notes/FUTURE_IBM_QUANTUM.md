# Future: IBM Quantum Real Hardware Integration

**Status:** Planned — NOT implemented yet. Quantum Hackathon future upgrade.

---

## Current Architecture

| Environment | Backend | Notes |
|---|---|---|
| Local dev | Qiskit Aer simulator (WS-QAOA) | Full quantum simulation — works now |
| Vercel serverless | Classical SLSQP + greedy | Fallback — Vercel 250MB limit |

---

## Upgrade Path: Aer → IBM Quantum Real Hardware

### 1. Replace sampler in `core/wsqaoa.py`

```python
# Current (Aer)
from qiskit_aer.primitives import SamplerV2 as AerSamplerV2
sampler = AerSamplerV2(default_shots=shots, seed=seed)

# Future (IBM Quantum Cloud)
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as RuntimeSampler
from qiskit_ibm_runtime import Options

service = QiskitRuntimeService(channel="ibm_quantum", token=os.environ["IBMQ_TOKEN"])
backend = service.least_busy(simulator=False, operational=True, min_num_qubits=N)
sampler = RuntimeSampler(mode=backend)
```

### 2. Circuit constraints for real hardware
- Limit `p=1` or `p=2` (deeper circuits → more decoherence)
- Transpile for native gate set: `transpile(qc, backend, optimization_level=3)`
- Add M3 readout error mitigation

### 3. Add error mitigation
```python
from qiskit_ibm_runtime import Options
options = Options()
options.resilience_level = 1  # M3 readout correction
```

### 4. Environment variables needed
```
IBMQ_TOKEN=your_ibm_quantum_api_token
IBMQ_BACKEND=ibm_kyiv  # or ibm_sherbrooke, ibm_brisbane
```

### 5. New packages (add to requirements.txt when ready)
```
qiskit-ibm-runtime>=0.20
```

---

## Notes
- Vercel serverless will ALWAYS use the classical fallback (250MB limit — qiskit won't fit)
- IBM Quantum jobs run from local dev or a proper server (Railway, Fly.io, self-hosted)
- Real hardware results will differ from Aer — add noise-aware post-processing
- Consider shot budget: real hardware shots are rate-limited (use 512-1024 shots max)
