from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import base64
import io
import matplotlib
import asyncio
from concurrent.futures import ThreadPoolExecutor
from qiskit import QuantumCircuit
from qiskit.qasm.exceptions import QasmError
from qiskit.visualization import plot_histogram, circuit_drawer
from qiskit_ibm_runtime import Sampler

matplotlib.use("Agg")
import matplotlib.pyplot as plt

app = FastAPI(title="Secure Quantum Circuit Simulator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor()

class SimulationRequest(BaseModel):
    qasm: str = Field(..., description="Quantum circuit in QASM format")
    shots: Optional[int] = Field(1024, gt=0, le=8192, description="Number of shots for simulation")

async def run_sampler_async(qc: QuantumCircuit, shots: int):
    sampler = Sampler()
    loop = asyncio.get_event_loop()
    job = await loop.run_in_executor(executor, sampler.run, qc, shots)
    return job.result()

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

@app.get("/")
async def root():
    return {"message": "Secure Quantum Circuit Simulator API"}

@app.post("/simulate")
async def simulate(req: SimulationRequest) -> Dict[str, Any]:
    try:
        # Parse QASM safely
        qc = QuantumCircuit.from_qasm_str(req.qasm)
    except QasmError as e:
        raise HTTPException(status_code=400, detail=f"Invalid QASM input: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing circuit: {str(e)}")

    try:
        result = await run_sampler_async(qc, req.shots)
        counts = result.quasi_dists[0]

        circuit_img = circuit_drawer(qc, output="mpl")
        histogram = plot_histogram(counts)

        return {
            "circuit_image_base64": fig_to_base64(circuit_img),
            "histogram_image_base64": fig_to_base64(histogram),
            "counts": counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

