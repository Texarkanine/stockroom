"""O9 smoke test: prove the locked-minus-torch env can still embed locally.

Run inside the spike venv (after torch is provided out-of-band):
    uv run --no-sync python smoke.py
"""

import os


def main() -> None:
    import torch

    print("torch", torch.__version__)
    print("cuda available", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("device", torch.cuda.get_device_name(0))

    # Prove the model loads from local cache with no network (privacy posture).
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    vec = model.encode(["auth race condition in the login flow"])
    print("sentence-transformers OK; embedding shape", vec.shape)


if __name__ == "__main__":
    main()
