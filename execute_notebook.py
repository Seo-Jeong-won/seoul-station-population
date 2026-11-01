from pathlib import Path
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

sys.stdout.reconfigure(encoding='utf-8')
here=Path(__file__).resolve().parent
path=here/'analysis.ipynb'
notebook=nbformat.read(path,as_version=4)
manager=KernelManager(kernel_name='python3')
manager.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
client=NotebookClient(notebook,km=manager,timeout=180,resources={'metadata':{'path':str(here)}})
try:
    client.execute()
finally:
    nbformat.write(notebook,path)
codes=[c for c in notebook.cells if c.cell_type=='code']
assert all(c.execution_count is not None for c in codes)
assert not any(o.output_type=='error' for c in codes for o in c.outputs)
print(f'Executed {len(codes)} code cells successfully.')
