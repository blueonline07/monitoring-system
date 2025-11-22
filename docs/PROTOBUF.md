# Protocol Buffer Generation

## Regenerating gRPC Code

If you modify `monitoring.proto`, regenerate the Python code with:

```bash
cd shared
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. monitoring.proto
```

## Important: Fix Import After Generation

After regenerating, you must fix the import in `monitoring_pb2_grpc.py`:

**Change this line:**
```python
import monitoring_pb2 as monitoring__pb2
```

**To this:**
```python
from . import monitoring_pb2 as monitoring__pb2
```

This is required because we're using a package structure. The generated code uses absolute imports which don't work with our module layout.

## Alternative: Use sed to fix automatically

```bash
cd shared
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. monitoring.proto
sed -i '' 's/import monitoring_pb2/from . import monitoring_pb2/' monitoring_pb2_grpc.py
```

## Files Generated

- `monitoring_pb2.py` - Message class definitions
- `monitoring_pb2_grpc.py` - Service stubs and client/server code

Both files are auto-generated and should not be edited manually (except for the import fix).

