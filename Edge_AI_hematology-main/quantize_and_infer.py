import os, time, numpy as np

try:
    import onnx
    import onnxruntime as ort
    from onnxruntime.quantization import quantize_dynamic, QuantType
except ImportError:
    ort = None

def export_torch_to_onnx(model, dummy_input, output_path="outputs/model_fp32.onnx"):
    import torch
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    model.eval()
    torch.onnx.export(
        model, dummy_input, output_path,
        export_params=True, opset_version=14, do_constant_folding=True,
        input_names=["input"], output_names=["boxes", "scores", "labels"],
        dynamic_axes={"input": {0: "batch_size"}}
    )
    print(f"ONNX FP32 exported: {output_path}")
    return output_path

def quantize_onnx_to_int8(input_onnx_path, output_int8_path="outputs/model_int8.onnx"):
    if ort is None:
        raise RuntimeError("onnxruntime required for quantization.")
    os.makedirs(os.path.dirname(output_int8_path), exist_ok=True)
    quantize_dynamic(model_input=input_onnx_path, model_output=output_int8_path, weight_type=QuantType.QInt8)
    fp32_size = os.path.getsize(input_onnx_path) / (1024 * 1024)
    int8_size = os.path.getsize(output_int8_path) / (1024 * 1024)
    print(f"INT8 Quantization Complete! FP32: {fp32_size:.2f} MB -> INT8: {int8_size:.2f} MB")
    return output_int8_path

def profile_edge_inference(onnx_model_path, input_shape=(1, 3, 640, 640), num_runs=50):
    if ort is None:
        raise RuntimeError("onnxruntime required for profiling.")
    sess_options = ort.SessionOptions()
    sess_options.intra_op_num_threads = 4
    session = ort.InferenceSession(onnx_model_path, sess_options, providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    dummy_data = np.random.randn(*input_shape).astype(np.float32)
    for _ in range(5):
        session.run(None, {input_name: dummy_data})
    latencies = []
    for _ in range(num_runs):
        t0 = time.perf_counter()
        session.run(None, {input_name: dummy_data})
        t1 = time.perf_counter()
        latencies.append((t1 - t0) * 1000.0)
    avg_latency = float(np.mean(latencies))
    fps = 1000.0 / avg_latency
    return {
        "model_path": onnx_model_path,
        "avg_latency_ms": avg_latency,
        "fps": float(fps),
        "model_size_mb": float(os.path.getsize(onnx_model_path) / (1024 * 1024))
    }
