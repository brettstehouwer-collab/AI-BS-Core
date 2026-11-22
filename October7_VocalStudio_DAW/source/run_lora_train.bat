@echo off
title ACE-Step 1.5 LoRA Training (NVIDIA RTX 4090 24GB)
cd /d "%~dp0"

echo ============================================================
echo   ACE-Step 1.5 LoRA Training Launcher
echo   Target Device: NVIDIA GeForce RTX 4090 (24GB VRAM)
echo   Precision: BF16 Mixed Precision ^| 8-Bit AdamW Optimizer
echo ============================================================

set MODEL_PATH=./checkpoints/acestep_v1.5_xl_sft
set DATASET_DIR=./processed_dataset
set OUTPUT_DIR=./trained_loras/october7_lora_v1

if not exist "%DATASET_DIR%\metadata.jsonl" (
    echo [!] Dataset manifest not found. Slicing audio files first...
    python preprocess_dataset.py --input-dir . --output-dir %DATASET_DIR%
)

echo Starting Accelerate Launch on RTX 4090...
accelerate launch ^
  --mixed_precision=bf16 ^
  --num_processes=1 ^
  --num_machines=1 ^
  train_acestep_lora.py ^
    --pretrained_model_name_or_path="%MODEL_PATH%" ^
    --train_data_dir="%DATASET_DIR%" ^
    --metadata_file="%DATASET_DIR%/metadata.jsonl" ^
    --output_dir="%OUTPUT_DIR%" ^
    --lora_rank=32 ^
    --lora_alpha=64 ^
    --lora_dropout=0.05 ^
    --target_modules "to_q" "to_k" "to_v" "to_out.0" ^
    --train_batch_size=2 ^
    --gradient_accumulation_steps=8 ^
    --learning_rate=1.5e-4 ^
    --lr_scheduler="cosine_with_restarts" ^
    --lr_warmup_steps=120 ^
    --lr_num_cycles=2 ^
    --max_train_steps=2500 ^
    --checkpointing_steps=250 ^
    --checkpoints_total_limit=3 ^
    --optimizer="adamw8bit" ^
    --weight_decay=1e-2 ^
    --max_grad_norm=1.0 ^
    --seed=42 ^
    --logging_dir="%OUTPUT_DIR%/logs"

pause
