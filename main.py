from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import base64
import io
import matplotlib.pyplot as plt

# Qiskit imports
from qiskit import QuantumCircuit
from qiskit_ibm_runtime import Sampler
from qiskit.visualization import plot_histogram, circuit_drawer

# PennyLane imports
import pennylane as qml

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <h1>Quantum Circuit Simulator API</h1>
    <p>Use POST /simulate endpoint to run quantum circuits</p>
    """

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimulationRequest(BaseModel):
    code: str

@app.post("/simulate")
async def simulate(req: SimulationRequest):
    try:
        local_vars = {}
        exec(req.code, {}, local_vars)

        # Qiskit branch
        if "qc" in local_vars and isinstance(local_vars['qc'], QuantumCircuit):
            qc = local_vars['qc']
            sampler = Sampler()
            job = sampler.run(qc, shots=1024)
            result = job.result()
            counts = result.quasi_dists[0]

            circuit_img = circuit_drawer(qc, output="mpl")
            buf_circuit = io.BytesIO()
            circuit_img.savefig(buf_circuit, format='png')
            buf_circuit.seek(0)
            circuit_base64 = base64.b64encode(buf_circuit.read()).decode()

            histogram = plot_histogram(counts)
            buf_hist = io.BytesIO()
            histogram.savefig(buf_hist, format='png')
            buf_hist.seek(0)
            hist_base64 = base64.b64encode(buf_hist.read()).decode()

            return {
                "framework": "qiskit",
                "circuit_image_base64": circuit_base64,
                "histogram_image_base64": hist_base64,
                "counts": counts
            }

        # PennyLane branch
        if "qml_circuit" in local_vars:
            qml_circuit = local_vars['qml_circuit']
            qml_result = local_vars.get('qml_result', None)

            fig, ax = plt.subplots(figsize=(8, 2))
            drawing = qml.draw_mpl(qml_circuit)(*local_vars.get('qml_args', ())) if hasattr(qml, "draw_mpl") else qml_circuit.draw()
            if hasattr(drawing, 'savefig'):
                drawing.savefig(ax=ax)
            elif isinstance(drawing, str):
                ax.text(0.01, 0.5, drawing, fontsize=12, family='monospace')
            ax.axis('off')
            buf_circuit = io.BytesIO()
            fig.savefig(buf_circuit, format='png')
            buf_circuit.seek(0)
            circuit_base64 = base64.b64encode(buf_circuit.read()).decode()

            return {
                "framework": "pennylane",
                "circuit_image_base64": circuit_base64,
                "qml_result": str(qml_result)
            }

        return {"error": "No recognized quantum circuit found in provided code."}

    except Exception as e:
        return {"error": str(e)}



