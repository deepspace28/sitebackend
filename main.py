from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import io
from qiskit import QuantumCircuit, Aer, execute
from qiskit.visualization import plot_histogram, circuit_drawer
import matplotlib.pyplot as plt

app = FastAPI()

# Allow frontend (V0.dev) to call this backend without CORS issues
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimulationRequest(BaseModel):
    code: str

@app.post("/simulate")
async def simulate(req: SimulationRequest):
    try:
        # Execute the GPT-generated Qiskit code
        local_vars = {}
        exec(req.code, {}, local_vars)

        if "qc" not in local_vars:
            return {"error": "No QuantumCircuit named 'qc' found."}

        qc = local_vars['qc']

        # Simulate circuit
        backend = Aer.get_backend('qasm_simulator')
        job = execute(qc, backend, shots=1024)
        result = job.result()
        counts = result.get_counts(qc)

        # Plot circuit diagram
        circuit_img = circuit_drawer(qc, output="mpl")
        buf_circuit = io.BytesIO()
        circuit_img.savefig(buf_circuit, format='png')
        buf_circuit.seek(0)
        circuit_base64 = base64.b64encode(buf_circuit.read()).decode('utf-8')

        # Plot histogram
        histogram = plot_histogram(counts)
        buf_hist = io.BytesIO()
        histogram.savefig(buf_hist, format='png')
        buf_hist.seek(0)
        hist_base64 = base64.b64encode(buf_hist.read()).decode('utf-8')

        return {
            "circuit_image_base64": circuit_base64,
            "histogram_image_base64": hist_base64,
            "counts": counts
        }

    except Exception as e:
        return {"error": str(e)}