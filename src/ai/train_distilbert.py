"""
src/ai/train_distilbert.py
Fine-tuning DistilBERT for Multi-Discipline Engineering Review Comment Classification.
"""

import os
import sys
import time
import json
import csv
from pathlib import Path
from typing import List, Dict, Tuple

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup
)
from torch.optim import AdamW

# Ensure clean UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_DIR = PROJECT_ROOT / "dataset" / "classification_dataset"
MODEL_SAVE_DIR = PROJECT_ROOT / "models" / "distilbert_engineering_classifier"

CATEGORIES = [
    "Technical",
    "Drafting",
    "Dimension",
    "Cosmetic",
    "Standards",
    "Coordination",
    "Documentation",
    "Revision",
    "Calculation",
    "Feasibility",
    "Material",
    "Notes",
    "BOM"
]

CATEGORY_TO_ID = {cat: idx for idx, cat in enumerate(CATEGORIES)}
ID_TO_CATEGORY = {idx: cat for idx, cat in enumerate(CATEGORIES)}


class EngineeringCommentDataset(Dataset):
    """PyTorch Dataset for engineering review comments."""

    def __init__(self, csv_file: Path, tokenizer, max_length: int = 128):
        self.texts = []
        self.labels = []
        self.tokenizer = tokenizer
        self.max_length = max_length

        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                text = row["text"].strip()
                label = int(row["label"])
                if text:
                    self.texts.append(text)
                    self.labels.append(label)

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]

        encoding = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt"
        )

        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "label": torch.tensor(label, dtype=torch.long)
        }


def evaluate(model, val_loader, device):
    """Evaluates model on validation set."""
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    loss_fn = torch.nn.CrossEntropyLoss()

    with torch.no_grad():
        for batch in val_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["label"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            logits = outputs.logits

            total_loss += loss.item() * len(labels)
            preds = torch.argmax(logits, dim=1)
            correct += (preds == labels).sum().item()
            total += len(labels)

    avg_loss = total_loss / total if total > 0 else 0.0
    accuracy = correct / total if total > 0 else 0.0
    return avg_loss, accuracy


def train_distilbert(
    model_name: str = "distilbert-base-uncased",
    epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    max_length: int = 128
):
    """Main training and fine-tuning loop."""
    print("=" * 80)
    print(" [DISTILBERT FINE-TUNING PIPELINE: ENGINEERING CLASSIFICATION]")
    print("=" * 80)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        threads = min(8, os.cpu_count() or 4)
        torch.set_num_threads(threads)
        print(f"Using device: cpu (PyTorch CPU threads: {threads})")
    else:
        print(f"Using device: {device} ({torch.cuda.get_device_name(0)})")

    train_file = DATASET_DIR / "train.csv"
    val_file = DATASET_DIR / "val.csv"

    if not train_file.exists() or not val_file.exists():
        raise FileNotFoundError(f"Dataset CSV files not found in {DATASET_DIR}. Please run dataset_generator.py first.")

    print(f"\n1. Loading pretrained model & tokenizer: {model_name}...")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=len(CATEGORIES),
        id2label=ID_TO_CATEGORY,
        label2id=CATEGORY_TO_ID
    )
    model.to(device)

    print("2. Preparing DataLoaders...")
    train_dataset = EngineeringCommentDataset(train_file, tokenizer, max_length=max_length)
    val_dataset = EngineeringCommentDataset(val_file, tokenizer, max_length=max_length)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    print(f"   Train samples: {len(train_dataset)} | Val samples: {len(val_dataset)}")
    print(f"   Batch size: {batch_size} | Epochs: {epochs} | LR: {learning_rate}")

    optimizer = AdamW(model.parameters(), lr=learning_rate, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    warmup_steps = int(total_steps * 0.10)
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps)

    best_val_acc = 0.0
    training_history = []

    print("\n3. Starting Fine-Tuning Loop...")
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        correct_train = 0
        total_train = 0

        for step, batch in enumerate(train_loader, 1):
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["label"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            logits = outputs.logits

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            scheduler.step()

            train_loss += loss.item() * len(labels)
            preds = torch.argmax(logits, dim=1)
            correct_train += (preds == labels).sum().item()
            total_train += len(labels)

            if step % 25 == 0 or step == len(train_loader):
                print(f"   Epoch {epoch}/{epochs} | Step {step}/{len(train_loader)} | Batch Loss: {loss.item():.4f}")

        avg_train_loss = train_loss / total_train
        train_acc = correct_train / total_train

        val_loss, val_acc = evaluate(model, val_loader, device)

        print(f"\n--- Epoch {epoch}/{epochs} Summary ---")
        print(f"  Train Loss: {avg_train_loss:.4f} | Train Acc: {train_acc * 100:.2f}%")
        print(f"  Val Loss:   {val_loss:.4f} | Val Acc:   {val_acc * 100:.2f}%")

        epoch_stats = {
            "epoch": epoch,
            "train_loss": avg_train_loss,
            "train_acc": train_acc,
            "val_loss": val_loss,
            "val_acc": val_acc
        }
        training_history.append(epoch_stats)

        # Save checkpoint if best validation accuracy
        if val_acc >= best_val_acc:
            best_val_acc = val_acc
            print(f"  ⭐ Best model checkpoint updated! Saving to: {MODEL_SAVE_DIR}")
            MODEL_SAVE_DIR.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(MODEL_SAVE_DIR)
            tokenizer.save_pretrained(MODEL_SAVE_DIR)

            # Save metadata config
            meta = {
                "model_name": model_name,
                "num_classes": len(CATEGORIES),
                "categories": CATEGORIES,
                "best_val_accuracy": best_val_acc,
                "epochs_trained": epoch,
                "trained_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(MODEL_SAVE_DIR / "training_metadata.json", "w", encoding="utf-8") as mf:
                json.dump(meta, mf, indent=2)

    total_duration = round(time.time() - start_time, 1)
    print("\n" + "=" * 80)
    print(f" [TRAINING COMPLETE] Total time: {total_duration}s | Best Val Accuracy: {best_val_acc * 100:.2f}%")
    print(f" Model saved to: {MODEL_SAVE_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    train_distilbert(
        model_name="distilbert-base-uncased",
        epochs=3,
        batch_size=16,
        learning_rate=2e-5,
        max_length=128
    )
