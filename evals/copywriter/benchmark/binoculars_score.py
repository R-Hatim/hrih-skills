#!/usr/bin/env python3
"""Score texts with Binoculars (Hans et al., ICML 2024), one model at a time, on CPU or GPU.

Binoculars is a zero-shot detector: score = log-perplexity of the text under a "performer"
model divided by the cross-perplexity between an "observer" and the performer. Lower scores
look more machine-generated. This is a re-implementation of the scoring in
https://github.com/ahans30/Binoculars (BSD-3), using the paper's default pair
(observer tiiuae/falcon-7b, performer tiiuae/falcon-7b-instruct) and its published thresholds.

Unlike the reference code, it loads one model at a time (observer pass first, keeping its
next-token distributions in float16, then the performer pass), so two 7B models never sit in
memory together. That lets it run on a 64 GB machine without a big GPU.

Requirements (not standard library): torch, transformers, accelerate, safetensors.
Models: about 29 GB of safetensors downloaded from Hugging Face on first use (set HF_HOME to
choose where). Expect roughly 10-60 s per text per model on a modern laptop CPU.

Usage:
    python binoculars_score.py TEXT_DIR -o scores.json [--dtype bfloat16|float32] [--max-tokens 512]
    python binoculars_score.py a.txt b.txt -o scores.json
Every *.txt file in TEXT_DIR is scored. Output: JSON with one record per file plus run metadata.
"""
import argparse
import datetime as dt
import json
import os
import platform
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

OBSERVER = "tiiuae/falcon-7b"
PERFORMER = "tiiuae/falcon-7b-instruct"
# Published thresholds from the reference implementation (computed with bfloat16 on GPU).
THRESHOLD_LOW_FPR = 0.8536432310785527   # "low-fpr" mode: below this = flagged as machine
THRESHOLD_ACCURACY = 0.9015310749276843  # "accuracy" mode


def load_model(name, dtype, device):
    model = AutoModelForCausalLM.from_pretrained(name, torch_dtype=dtype, low_cpu_mem_usage=True)
    model.to(device)
    model.eval()
    return model


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("inputs", nargs="+", help="a folder of .txt files, or .txt files")
    ap.add_argument("-o", "--out", required=True, help="output JSON file")
    ap.add_argument("--dtype", default="bfloat16", choices=["bfloat16", "float32"],
                    help="bfloat16 matches the reference thresholds and needs ~15 GB per model; "
                         "float32 needs ~30 GB per model (Windows may refuse with 'paging file too small')")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--max-tokens", type=int, default=512, help="truncate texts to this many tokens (reference: 512)")
    ap.add_argument("--threads", type=int, default=0, help="torch CPU threads (0 = torch default)")
    args = ap.parse_args(argv)

    if args.threads:
        torch.set_num_threads(args.threads)
    files = []
    for item in args.inputs:
        p = Path(item)
        files += sorted(p.glob("*.txt")) if p.is_dir() else [p]
    if not files:
        sys.exit("No .txt files found.")
    texts = [f.read_text(encoding="utf-8").strip() for f in files]
    dtype = torch.float32 if args.dtype == "float32" else torch.bfloat16
    started = time.time()

    tokenizer = AutoTokenizer.from_pretrained(OBSERVER)
    encodings = [tokenizer(t, return_tensors="pt", truncation=True, max_length=args.max_tokens,
                           return_token_type_ids=False) for t in texts]

    # Pass 1: observer. Keep its next-token distributions (softmax) in float16.
    t0 = time.time()
    observer = load_model(OBSERVER, dtype, args.device)
    obs_probs = []
    with torch.inference_mode():
        for i, enc in enumerate(encodings):
            logits = observer(**{k: v.to(args.device) for k, v in enc.items()}).logits.float()
            obs_probs.append(torch.softmax(logits, dim=-1).to(torch.float16).cpu())
            print(f"[observer] {i + 1}/{len(files)} {files[i].name} ({enc.input_ids.shape[1]} tokens)", flush=True)
    del observer
    if args.device == "cuda":
        torch.cuda.empty_cache()
    observer_seconds = time.time() - t0

    # Pass 2: performer. Perplexity of the text, and cross-entropy against the observer's distribution.
    t0 = time.time()
    performer = load_model(PERFORMER, dtype, args.device)
    records = []
    with torch.inference_mode():
        for i, enc in enumerate(encodings):
            ids = enc.input_ids.to(args.device)
            logits = performer(**{k: v.to(args.device) for k, v in enc.items()}).logits.float()
            log_q = torch.log_softmax(logits, dim=-1)
            # log-perplexity: mean next-token cross-entropy under the performer (shifted by one)
            nll = -log_q[0, :-1, :].gather(-1, ids[0, 1:].unsqueeze(-1)).squeeze(-1)
            ppl = nll.mean().item()
            # cross-perplexity: mean over positions of H(observer_t, performer_t)
            p = obs_probs[i][0].to(log_q.device, torch.float32)
            x_ppl = (-(p * log_q[0]).sum(-1)).mean().item()
            score = ppl / x_ppl
            records.append({
                "file": files[i].name,
                "tokens": int(ids.shape[1]),
                "truncated": int(ids.shape[1]) >= args.max_tokens,
                "log_ppl": round(ppl, 5),
                "x_ppl": round(x_ppl, 5),
                "score": round(score, 5),
                "flag_low_fpr": score < THRESHOLD_LOW_FPR,
                "flag_accuracy": score < THRESHOLD_ACCURACY,
            })
            print(f"[performer] {i + 1}/{len(files)} {files[i].name}: score {score:.4f}", flush=True)
    performer_seconds = time.time() - t0

    out = {
        "detector": "binoculars",
        "observer": OBSERVER,
        "performer": PERFORMER,
        "thresholds": {"low_fpr": THRESHOLD_LOW_FPR, "accuracy": THRESHOLD_ACCURACY},
        "dtype": args.dtype,
        "device": args.device,
        "max_tokens": args.max_tokens,
        "torch": torch.__version__,
        "machine": platform.processor() or platform.machine(),
        "run_at": dt.datetime.now().isoformat(timespec="seconds"),
        "seconds": {"observer": round(observer_seconds), "performer": round(performer_seconds),
                    "total": round(time.time() - started)},
        "results": records,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} scores to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
