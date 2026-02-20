import os
import importlib.util

ROOT = os.path.dirname(os.path.dirname(__file__))
ra_path = os.path.join(ROOT, 'Result_Automation', 'automation.py')
input_folder = os.path.join(ROOT, 'Result_Automation', 'input_pdfs', 'IA1')
output_folder = os.path.join(ROOT, 'uploads', 'result_automation', 'output')

os.makedirs(output_folder, exist_ok=True)

spec = importlib.util.spec_from_file_location('ra', ra_path)
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)

print('Using automation module from:', ra_path)
print('Input folder:', input_folder)
print('Output folder:', output_folder)

try:
    out = ra.generate_report_flask('IA1', 'Test College', input_folder, output_folder)
    print('generate_report_flask returned:', out)
    if out and os.path.exists(out):
        print('Output file exists:', out)
    else:
        # list output folder
        print('Output folder contents:', os.listdir(output_folder))
except Exception as e:
    print('ERROR during report generation:', e)
