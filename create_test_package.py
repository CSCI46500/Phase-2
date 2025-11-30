import zipfile
import base64
import io

# Create a simple zip package
z = io.BytesIO()
with zipfile.ZipFile(z, 'w') as zf:
    zf.writestr('test_model.py', 'print("Hello from test package!")')
    zf.writestr('README.md', '# Test Package\nThis is a test package for RDS/S3 integration.')

z.seek(0)
b64_content = base64.b64encode(z.read()).decode()

print(b64_content)
